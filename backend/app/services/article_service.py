# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import math
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy import and_, cast, func, or_, select, update
from sqlalchemy import String as SAString
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article, FulltextStatus
from app.models.article_user_state import ArticleUserState
from app.models.category import Category
from app.models.feed import Feed
from app.models.user_feed import UserFeed
from app.schemas.article import (
    ArticleDetail,
    ArticleListItem,
    ArticleListResponse,
    ArticleStateUpdate,
    FrontPageColumn,
    FrontPageResponse,
)
from app.services import full_text as fulltext_svc
from app.services.ranking import compute_category_affinity, score_article, topic_weight
from app.services.vote_service import get_topic_preferences, get_user_vote, load_user_votes_bulk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_list_item(
    article: Article,
    feed_title: str | None,
    state: ArticleUserState | None,
    user_vote: int = 0,
) -> ArticleListItem:
    return ArticleListItem(
        id=article.id,
        feed_id=article.feed_id,
        feed_title=feed_title,
        title=article.title,
        url=article.url,
        author=article.author,
        content_excerpt=article.content_excerpt,
        language=article.language,
        tags=article.tags or [],
        published_at=article.published_at,
        fetched_at=article.fetched_at,
        is_read=state.is_read if state else False,
        is_starred=state.is_starred if state else False,
        is_archived=state.is_archived if state else False,
        user_vote=user_vote,
    )


def _base_stmt(user_id: UUID, subscribed_only: bool):
    """Return the core SELECT with joins, ready for WHERE clauses to be added."""
    stmt = (
        select(Article, Feed.title.label("feed_title"), ArticleUserState)
        .join(Feed, Article.feed_id == Feed.id)
        .outerjoin(
            ArticleUserState,
            and_(
                ArticleUserState.article_id == Article.id,
                ArticleUserState.user_id == user_id,
            ),
        )
    )
    if subscribed_only:
        stmt = stmt.join(
            UserFeed,
            and_(UserFeed.feed_id == Feed.id, UserFeed.user_id == user_id),
        )
    return stmt


def _apply_filters(stmt, *, feed_id, category_id, tags, is_read, is_starred, is_archived, search):
    if feed_id is not None:
        stmt = stmt.where(Article.feed_id == feed_id)
    if category_id is not None:
        stmt = stmt.where(Feed.category_id == category_id)
    if tags:
        # Portable JSON array membership: cast the JSON column to text and use LIKE.
        # Stored as '["tag1","tag2"]' so matching on '"tag"' is accurate.
        for tag in tags:
            stmt = stmt.where(cast(Article.tags, SAString).like(f'%"{tag}"%'))
    if is_read is not None:
        if is_read:
            stmt = stmt.where(
                and_(ArticleUserState.is_read == True)  # noqa: E712
            )
        else:
            stmt = stmt.where(
                or_(
                    ArticleUserState.is_read == False,  # noqa: E712
                    ArticleUserState.is_read.is_(None),
                )
            )
    if is_starred is not None:
        if is_starred:
            stmt = stmt.where(ArticleUserState.is_starred == True)  # noqa: E712
        else:
            stmt = stmt.where(
                or_(
                    ArticleUserState.is_starred == False,  # noqa: E712
                    ArticleUserState.is_starred.is_(None),
                )
            )
    if is_archived is not None:
        if is_archived:
            stmt = stmt.where(ArticleUserState.is_archived == True)  # noqa: E712
        else:
            stmt = stmt.where(
                or_(
                    ArticleUserState.is_archived == False,  # noqa: E712
                    ArticleUserState.is_archived.is_(None),
                )
            )
    if search:
        term = f"%{search}%"
        stmt = stmt.where(
            or_(
                Article.title.ilike(term),
                Article.content_excerpt.ilike(term),
            )
        )
    return stmt


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_articles(
    db: AsyncSession,
    user_id: UUID,
    feed_id: UUID | None = None,
    category_id: UUID | None = None,
    tags: list[str] | None = None,
    is_read: bool | None = None,
    is_starred: bool | None = None,
    is_archived: bool | None = None,
    subscribed_only: bool = True,
    search: str | None = None,
    page: int = 1,
    size: int = 20,
    order_by: Literal["published_at", "fetched_at"] = "published_at",
    order_dir: Literal["asc", "desc"] = "desc",
) -> ArticleListResponse:
    base = _base_stmt(user_id, subscribed_only)
    base = _apply_filters(
        base,
        feed_id=feed_id,
        category_id=category_id,
        tags=tags,
        is_read=is_read,
        is_starred=is_starred,
        is_archived=is_archived,
        search=search,
    )

    # Total count (same filters)
    count_stmt = select(func.count()).select_from(base.subquery())
    total: int = (await db.scalar(count_stmt)) or 0

    # Unread count (same filters minus any is_read filter)
    unread_base = _base_stmt(user_id, subscribed_only)
    unread_base = _apply_filters(
        unread_base,
        feed_id=feed_id,
        category_id=category_id,
        tags=tags,
        is_read=None,  # ignore read filter for the count
        is_starred=is_starred,
        is_archived=is_archived,
        search=search,
    )
    unread_base = unread_base.where(
        or_(
            ArticleUserState.is_read == False,  # noqa: E712
            ArticleUserState.is_read.is_(None),
        )
    )
    unread_count_stmt = select(func.count()).select_from(unread_base.subquery())
    unread_count: int = (await db.scalar(unread_count_stmt)) or 0

    # Ordering
    order_col = Article.published_at if order_by == "published_at" else Article.fetched_at
    if order_dir == "desc":
        base = base.order_by(order_col.desc().nulls_last())
    else:
        base = base.order_by(order_col.asc().nulls_last())

    # Pagination
    offset = (page - 1) * size
    paged = base.offset(offset).limit(size)

    rows = (await db.execute(paged)).all()

    # Bulk load votes for this page
    article_ids = [row.Article.id for row in rows]
    votes = await load_user_votes_bulk(db, user_id, article_ids)

    items = [
        _build_list_item(
            row.Article,
            row.feed_title,
            row.ArticleUserState,
            user_vote=votes.get(row.Article.id, 0),
        )
        for row in rows
    ]

    pages = math.ceil(total / size) if size > 0 else 1
    return ArticleListResponse(
        items=items,
        total=total,
        page=page,
        pages=max(pages, 1),
        unread_count=unread_count,
    )


def _schedule_fulltext(article_id: UUID) -> None:
    """Thin wrapper so tests can patch this without touching asyncio globally."""
    asyncio.create_task(fulltext_svc.fetch_fulltext(article_id))


async def get_article_detail(
    db: AsyncSession, article_id: UUID, user_id: UUID
) -> ArticleDetail | None:
    result = await db.execute(
        select(Article, Feed.title.label("feed_title"), ArticleUserState)
        .join(Feed, Article.feed_id == Feed.id)
        .outerjoin(
            ArticleUserState,
            and_(
                ArticleUserState.article_id == Article.id,
                ArticleUserState.user_id == user_id,
            ),
        )
        .where(Article.id == article_id)
    )
    row = result.first()
    if row is None:
        return None

    article: Article = row.Article
    feed_title: str | None = row.feed_title
    state: ArticleUserState | None = row.ArticleUserState

    # Trigger fulltext fetch if not yet available
    fulltext_loading = False
    if (
        article.fulltext_status == FulltextStatus.PENDING.value
        and article.content_fulltext is None
        and article.url is not None
    ):
        fulltext_loading = True
        if not fulltext_svc.is_fetch_active(article_id):
            _schedule_fulltext(article_id)

    user_vote = await get_user_vote(db, user_id, article_id)

    return ArticleDetail(
        id=article.id,
        feed_id=article.feed_id,
        feed_title=feed_title,
        title=article.title,
        url=article.url,
        author=article.author,
        content_excerpt=article.content_excerpt,
        language=article.language,
        tags=article.tags or [],
        published_at=article.published_at,
        fetched_at=article.fetched_at,
        is_read=state.is_read if state else False,
        is_starred=state.is_starred if state else False,
        is_archived=state.is_archived if state else False,
        user_vote=user_vote,
        content_fulltext=article.content_fulltext,
        fulltext_status=article.fulltext_status,
        fulltext_loading=fulltext_loading,
        tags_source=article.tags_source,
    )


async def update_article_state(
    db: AsyncSession,
    article_id: UUID,
    user_id: UUID,
    update_data: ArticleStateUpdate,
) -> ArticleUserState:
    state = await db.get(ArticleUserState, (user_id, article_id))
    if state is None:
        state = ArticleUserState(
            user_id=user_id,
            article_id=article_id,
            is_read=False,
            is_starred=False,
            is_archived=False,
        )
        db.add(state)

    was_read = state.is_read

    if update_data.is_read is not None:
        state.is_read = update_data.is_read
        if update_data.is_read and not was_read:
            state.read_at = datetime.utcnow()
    if update_data.is_starred is not None:
        state.is_starred = update_data.is_starred
    if update_data.is_archived is not None:
        state.is_archived = update_data.is_archived

    await db.commit()
    await db.refresh(state)
    return state


async def mark_feed_read(
    db: AsyncSession,
    feed_id: UUID,
    user_id: UUID,
    before: datetime | None = None,
) -> int:
    """Bulk-mark all (or up-to-before) articles in a feed as read for a user."""
    article_query = select(Article.id).where(Article.feed_id == feed_id)
    if before is not None:
        article_query = article_query.where(Article.published_at <= before)

    article_ids = (await db.scalars(article_query)).all()
    if not article_ids:
        return 0

    now = datetime.utcnow()
    count = 0
    for aid in article_ids:
        state = await db.get(ArticleUserState, (user_id, aid))
        if state is None:
            state = ArticleUserState(
                user_id=user_id,
                article_id=aid,
                is_read=True,
                read_at=now,
            )
            db.add(state)
            count += 1
        elif not state.is_read:
            state.is_read = True
            state.read_at = now
            count += 1

    await db.commit()
    return count


async def get_frontpage_articles(
    db: AsyncSession, user_id: UUID, lang: str
) -> FrontPageResponse:
    """
    Scoring-based front page from the last 48 hours of subscribed feeds.
    topic_prefs and category_affinity are loaded once per request.
    """
    cutoff = datetime.utcnow() - timedelta(hours=48)

    result = await db.execute(
        select(Article, Feed, ArticleUserState, Category)
        .join(Feed, Article.feed_id == Feed.id)
        .join(
            UserFeed,
            and_(UserFeed.feed_id == Feed.id, UserFeed.user_id == user_id),
        )
        .outerjoin(
            ArticleUserState,
            and_(
                ArticleUserState.article_id == Article.id,
                ArticleUserState.user_id == user_id,
            ),
        )
        .outerjoin(Category, Feed.category_id == Category.id)
        .where(Article.published_at >= cutoff)
        .order_by(Article.published_at.desc())
    )
    rows = result.all()

    if not rows:
        return FrontPageResponse(
            hero=None,
            second_row=[],
            columns=[],
            digest_available=False,
            digest_id=None,
        )

    # Preload once per request — avoids O(N) extra queries
    affinity = await compute_category_affinity(db, user_id)
    topic_prefs = await get_topic_preferences(db, user_id)
    article_ids = [row.Article.id for row in rows]
    votes = await load_user_votes_bulk(db, user_id, article_ids)

    # Score each article
    scored: list[tuple[float, Article, str | None, ArticleUserState | None, Category | None]] = []
    for row in rows:
        article: Article = row.Article
        feed: Feed = row.Feed
        state: ArticleUserState | None = row.ArticleUserState
        category: Category | None = row.Category

        cat_id = feed.category_id
        cat_aff = affinity.get(cat_id, 1.0) if cat_id else 1.0
        t_w = topic_weight(article.tags or [], topic_prefs)

        s = score_article(
            published_at=article.published_at,
            source_weight=feed.source_weight,
            category_affinity=cat_aff,
            topic_weight_factor=t_w,
            is_read=state.is_read if state else False,
        )
        scored.append((s, article, feed.title, state, category))

    scored.sort(key=lambda x: x[0], reverse=True)

    def _to_item(s_tuple) -> ArticleListItem:
        _, article, feed_title, state, _ = s_tuple
        return _build_list_item(article, feed_title, state, user_vote=votes.get(article.id, 0))

    hero: ArticleListItem | None = None
    second_row: list[ArticleListItem] = []
    columns_map: dict[str, dict] = {}

    if scored:
        hero = _to_item(scored[0])
        remaining = scored[1:]
    else:
        remaining = []

    second_row = [_to_item(t) for t in remaining[:3]]
    remaining = remaining[3:]

    for s_tuple in remaining:
        _, article, feed_title, state, category = s_tuple
        if category is None:
            continue
        slug = category.slug
        if slug not in columns_map:
            name_dict: dict = category.name or {}
            cat_name = name_dict.get(lang) or name_dict.get("en") or slug
            columns_map[slug] = {"name": cat_name, "articles": []}
        if len(columns_map[slug]["articles"]) < 3:
            columns_map[slug]["articles"].append(
                _build_list_item(article, feed_title, state, user_vote=votes.get(article.id, 0))
            )

    columns = [
        FrontPageColumn(
            category_slug=slug,
            category_name=data["name"],
            articles=data["articles"],
        )
        for slug, data in columns_map.items()
    ]

    return FrontPageResponse(
        hero=hero,
        second_row=second_row,
        columns=columns,
        digest_available=False,
        digest_id=None,
    )
