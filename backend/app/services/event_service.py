# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Server-side event front-page grouping — structural parallel to
article_service.get_frontpage_articles, but scoring/grouping Events instead
of Articles. Layout stays server-driven (hero / second_row / columns), which
the frontend consumes as-is."""
from collections import defaultdict
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.article import Article
from app.models.article_user_state import ArticleUserState
from app.models.event import Event
from app.models.feed import Feed
from app.schemas.article import ArticleListItem
from app.schemas.event import EventDetail, EventFrontPageColumn, EventFrontPageResponse, EventListItem
from app.services.article_service import _build_list_item
from app.services.event_vote_service import load_user_event_votes_bulk
from app.services.ranking import compute_category_affinity, event_score, topic_weight
from app.services.vote_service import get_topic_preferences


def _build_event_list_item(event: Event, lang: str, user_vote: int) -> EventListItem:
    category_name = None
    if event.category and event.category.name:
        category_name = event.category.name.get(lang) or event.category.name.get("en")
    return EventListItem(
        id=event.id,
        title=event.title,
        title_source=event.title_source,
        synopsis=event.synopsis,
        tags=event.tags or [],
        category_id=event.category_id,
        category_name=category_name,
        status=event.status,
        article_count=event.article_count,
        source_count=event.source_count,
        opened_at=event.opened_at,
        last_activity_at=event.last_activity_at,
        user_vote=user_vote,
    )


async def get_frontpage_events(
    db: AsyncSession, user_id: UUID, lang: str, window_hours: int = 48
) -> EventFrontPageResponse:
    cutoff = datetime.utcnow() - timedelta(hours=window_hours)

    result = await db.execute(
        select(Event)
        .where(Event.last_activity_at >= cutoff)
        .options(selectinload(Event.category))
        .order_by(Event.last_activity_at.desc())
    )
    events = list(result.scalars().all())

    if not events:
        return EventFrontPageResponse(hero=None, second_row=[], columns=[])

    event_ids = [e.id for e in events]

    affinity = await compute_category_affinity(db, user_id)
    topic_prefs = await get_topic_preferences(db, user_id)
    votes = await load_user_event_votes_bulk(db, user_id, event_ids)

    member_rows = (
        await db.execute(
            select(Article.event_id, Feed.source_weight, ArticleUserState.is_read)
            .join(Feed, Article.feed_id == Feed.id)
            .outerjoin(
                ArticleUserState,
                and_(
                    ArticleUserState.article_id == Article.id,
                    ArticleUserState.user_id == user_id,
                ),
            )
            .where(Article.event_id.in_(event_ids))
        )
    ).all()

    per_event_source_weight: dict[UUID, float] = defaultdict(lambda: 1.0)
    per_event_read_states: dict[UUID, list[bool]] = defaultdict(list)
    for row in member_rows:
        per_event_source_weight[row.event_id] = max(
            per_event_source_weight[row.event_id], row.source_weight or 1.0
        )
        per_event_read_states[row.event_id].append(bool(row.is_read))

    scored: list[tuple[float, Event]] = []
    for event in events:
        cat_aff = affinity.get(event.category_id, 1.0) if event.category_id else 1.0
        t_w = topic_weight(event.tags or [], topic_prefs)
        s = event_score(
            last_activity_at=event.last_activity_at,
            source_weight=per_event_source_weight.get(event.id, 1.0),
            category_affinity=cat_aff,
            topic_weight_factor=t_w,
            source_count=event.source_count,
            read_states=per_event_read_states.get(event.id, []),
        )
        scored.append((s, event))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    def _to_item(event: Event) -> EventListItem:
        return _build_event_list_item(event, lang, votes.get(event.id, 0))

    hero: EventListItem | None = None
    remaining = scored
    if scored:
        hero = _to_item(scored[0][1])
        remaining = scored[1:]

    second_row = [_to_item(e) for _, e in remaining[:3]]
    remaining = remaining[3:]

    columns_map: dict[str, dict] = {}
    for _, event in remaining:
        if event.category is None:
            continue
        slug = event.category.slug
        if slug not in columns_map:
            name_dict = event.category.name or {}
            cat_name = name_dict.get(lang) or name_dict.get("en") or slug
            columns_map[slug] = {"name": cat_name, "events": []}
        if len(columns_map[slug]["events"]) < 3:
            columns_map[slug]["events"].append(_to_item(event))

    columns = [
        EventFrontPageColumn(category_slug=slug, category_name=data["name"], events=data["events"])
        for slug, data in columns_map.items()
    ]

    return EventFrontPageResponse(hero=hero, second_row=second_row, columns=columns)


async def get_event_detail(db: AsyncSession, event_id: UUID, user_id: UUID, lang: str) -> EventDetail | None:
    # Explicit select() + selectinload rather than db.get(): if the Event is
    # already in the session's identity map (e.g. loaded plainly earlier in
    # the same request, as admin merge/detach do), db.get() would skip
    # re-applying loader options and leave `category` unloaded, causing a
    # lazy-load attempt outside the async greenlet context.
    result = await db.execute(
        select(Event).where(Event.id == event_id).options(selectinload(Event.category))
    )
    event = result.scalar_one_or_none()
    if event is None:
        return None

    rows = (
        await db.execute(
            select(Article, Feed.title.label("feed_title"), ArticleUserState)
            .join(Feed, Article.feed_id == Feed.id)
            .outerjoin(
                ArticleUserState,
                and_(
                    ArticleUserState.article_id == Article.id,
                    ArticleUserState.user_id == user_id,
                ),
            )
            .where(Article.event_id == event_id)
            .order_by(Article.published_at.desc())
        )
    ).all()

    articles: list[ArticleListItem] = [
        _build_list_item(row.Article, row.feed_title, row.ArticleUserState) for row in rows
    ]

    from app.services.event_vote_service import get_user_vote

    user_vote = await get_user_vote(db, user_id, event_id)
    base = _build_event_list_item(event, lang, user_vote)
    return EventDetail(**base.model_dump(), articles=articles)


async def get_event_articles(db: AsyncSession, event_id: UUID, user_id: UUID) -> list[ArticleListItem] | None:
    event = await db.get(Event, event_id)
    if event is None:
        return None
    detail = await get_event_detail(db, event_id, user_id, lang="it")
    return detail.articles if detail else []
