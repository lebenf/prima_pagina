# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import math
import re
from uuid import UUID

from sqlalchemy import Integer, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.article import Article
from app.models.article_user_state import ArticleUserState
from app.models.feed import Feed
from app.models.user_feed import UserFeed
from app.schemas.search import SearchFilters, SearchResponse, SearchResultItem
from app.services.vote_service import load_user_votes_bulk


async def search_articles(
    db: AsyncSession,
    user_id: UUID,
    filters: SearchFilters,
    db_dialect: str = "sqlite",
) -> SearchResponse:
    q = filters.q.strip().lower()

    base_stmt = (
        select(Article)
        .join(Feed, Article.feed_id == Feed.id)
        .join(
            UserFeed,
            and_(
                UserFeed.feed_id == Feed.id,
                UserFeed.user_id == user_id,
            ),
        )
        .options(
            selectinload(Article.feed),
            selectinload(Article.user_states),
        )
    )

    if filters.feed_id:
        base_stmt = base_stmt.where(Article.feed_id == filters.feed_id)
    if filters.category_id:
        base_stmt = base_stmt.where(Feed.category_id == filters.category_id)
    if filters.date_from:
        base_stmt = base_stmt.where(Article.published_at >= filters.date_from)
    if filters.date_to:
        base_stmt = base_stmt.where(Article.published_at <= filters.date_to)

    if db_dialect == "postgresql":
        search_condition = _pg_search_condition(q)
        order_clause = _pg_relevance_order(q)
    else:
        search_condition = _sqlite_search_condition(q)
        order_clause = _sqlite_relevance_order(q)

    count_stmt = select(func.count()).select_from(
        base_stmt.where(search_condition).subquery()
    )
    total = (await db.execute(count_stmt)).scalar_one()

    result_stmt = (
        base_stmt
        .where(search_condition)
        .order_by(order_clause, Article.published_at.desc())
        .offset((filters.page - 1) * filters.size)
        .limit(filters.size)
    )
    result = await db.execute(result_stmt)
    articles = result.scalars().all()

    votes = await load_user_votes_bulk(db, user_id, [a.id for a in articles])

    items = [
        _to_search_result(article, q, user_id, votes.get(article.id, 0))
        for article in articles
    ]

    return SearchResponse(
        items=items,
        total=total,
        page=filters.page,
        pages=math.ceil(total / filters.size) if total > 0 else 0,
        query=filters.q,
    )


# ── SQLite ────────────────────────────────────────────────────────────────


def _sqlite_search_condition(q: str):
    return or_(
        func.lower(Article.title).contains(q),
        func.lower(Article.content_excerpt).contains(q),
    )


def _sqlite_relevance_order(q: str):
    title_match = func.lower(Article.title).contains(q).cast(Integer)
    return title_match.desc()


# ── PostgreSQL ────────────────────────────────────────────────────────────


def _pg_search_condition(q: str):
    ts_query = func.plainto_tsquery("simple", q)
    ts_vector = func.to_tsvector(
        "simple",
        func.coalesce(Article.title, "") + " " + func.coalesce(Article.content_excerpt, ""),
    )
    return ts_vector.op("@@")(ts_query)


def _pg_relevance_order(q: str):
    ts_query = func.plainto_tsquery("simple", q)
    ts_vector = func.to_tsvector(
        "simple",
        func.coalesce(Article.title, "") + " " + func.coalesce(Article.content_excerpt, ""),
    )
    return func.ts_rank(ts_vector, ts_query).desc()


# ── Highlighting ──────────────────────────────────────────────────────────


def _highlight_text(text: str, query: str, max_length: int = 200) -> str:
    if not text:
        return ""
    lower_text = text.lower()
    pos = lower_text.find(query.lower())

    if pos == -1:
        snippet = _escape_html(text[:max_length])
        if len(text) > max_length:
            snippet += "…"
        return snippet

    start = max(0, pos - 80)
    end = min(len(text), pos + len(query) + 80)
    snippet = text[start:end]

    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""

    highlighted = re.sub(
        re.escape(query),
        lambda m: f"<mark>{_escape_html(m.group())}</mark>",
        _escape_html(snippet),
        flags=re.IGNORECASE,
    )
    return prefix + highlighted + suffix


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _to_search_result(
    article: Article,
    query: str,
    user_id: UUID,
    user_vote: int,
) -> SearchResultItem:
    state = next(
        (s for s in article.user_states if s.user_id == user_id),
        None,
    )
    return SearchResultItem(
        id=article.id,
        feed_id=article.feed_id,
        feed_title=article.feed.title if article.feed else None,
        title=article.title,
        title_highlighted=_highlight_text(article.title or "", query, max_length=200),
        excerpt_snippet=_highlight_text(article.content_excerpt or "", query, max_length=300),
        url=article.url,
        published_at=article.published_at,
        language=article.language,
        tags=article.tags or [],
        is_read=state.is_read if state else False,
        is_starred=state.is_starred if state else False,
        user_vote=user_vote,
    )
