# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from typing import Any

from sqlalchemy import String, and_, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.article import Article
from app.models.category import Category
from app.models.feed import Feed
from app.models.virtual_feed import VirtualFeed


async def get_virtual_feed_articles(
    db: AsyncSession,
    virtual_feed: VirtualFeed,
    limit: int = 50,
    offset: int = 0,
) -> list[Article]:
    stmt = _build_query(virtual_feed)
    stmt = (
        stmt
        .options(selectinload(Article.feed))
        .order_by(Article.published_at.desc(), Article.fetched_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_virtual_feed_articles(
    db: AsyncSession,
    virtual_feed: VirtualFeed,
) -> int:
    from sqlalchemy import func
    sub = _build_query(virtual_feed).subquery()
    result = await db.execute(select(func.count()).select_from(sub))
    return result.scalar_one()


def _build_query(virtual_feed: VirtualFeed):
    ft = virtual_feed.filter_type
    fc = virtual_feed.filter_config or {}

    base = select(Article).join(Feed, Article.feed_id == Feed.id)

    if ft == "category":
        cat_id = fc.get("category_id")
        return base.where(Feed.category_id == uuid.UUID(str(cat_id)))

    elif ft == "tags":
        tags = fc.get("tags", [])
        operator = fc.get("operator", "OR")
        return base.where(_tags_condition(tags, operator))

    elif ft == "mixed":
        conditions = []
        cats = fc.get("categories", [])
        tags = fc.get("tags", [])
        operator = fc.get("operator", "OR")

        if cats:
            cat_uuids = [uuid.UUID(str(c)) for c in cats]
            conditions.append(Feed.category_id.in_(cat_uuids))
        if tags:
            conditions.append(_tags_condition(tags, operator))

        if not conditions:
            return base.where(False)  # type: ignore[arg-type]

        if operator == "AND":
            return base.where(and_(*conditions))
        return base.where(or_(*conditions))

    return base


def _tags_condition(tags: list[str], operator: str):
    """
    Pragmatic JSON text search compatible with both SQLite and PostgreSQL.
    Uses LIKE on the serialized JSON string — accurate for quoted tag strings.
    """
    conditions = [cast(Article.tags, String).like(f'%"{tag}"%') for tag in tags]
    if operator == "AND":
        return and_(*conditions)
    return or_(*conditions)


async def validate_filter_config(
    db: AsyncSession,
    filter_type: str,
    filter_config: dict,
) -> None:
    """DB-level validation: check that referenced category IDs exist."""
    if filter_type == "category":
        cat_id = filter_config.get("category_id")
        if cat_id:
            cat = await db.get(Category, uuid.UUID(str(cat_id)))
            if not cat:
                raise ValueError(f"Category {cat_id} not found")

    elif filter_type == "mixed":
        for cat_id in filter_config.get("categories", []):
            cat = await db.get(Category, uuid.UUID(str(cat_id)))
            if not cat:
                raise ValueError(f"Category {cat_id} not found")
