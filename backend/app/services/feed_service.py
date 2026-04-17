import asyncio
import logging
import xml.etree.ElementTree as ET
from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feed import Feed
from app.models.user_feed import UserFeed
from app.schemas.common import Page
from app.schemas.feed import FeedCreate, FeedResponse, FeedUpdate, SubscriptionUpdate

logger = logging.getLogger(__name__)

_RSS_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "rss": "",
}


async def try_autodiscover_feed_info(url: str) -> dict:
    """Fetch the feed URL and extract title/site_url/language. Never raises."""
    result: dict = {}
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"Accept": "application/rss+xml, application/atom+xml, */*"})
            resp.raise_for_status()
            content = resp.text
    except Exception as exc:
        logger.debug("Auto-discovery failed for %s: %s", url, exc)
        return result

    try:
        root = ET.fromstring(content)
        tag = root.tag.lower()

        # Atom
        if "atom" in tag or root.tag == "{http://www.w3.org/2005/Atom}feed":
            ns = "http://www.w3.org/2005/Atom"
            title_el = root.find(f"{{{ns}}}title")
            if title_el is not None and title_el.text:
                result["title"] = title_el.text.strip()
            link_el = root.find(f"{{{ns}}}link[@rel='alternate']")
            if link_el is None:
                link_el = root.find(f"{{{ns}}}link")
            if link_el is not None:
                result["site_url"] = link_el.get("href", "")
            lang_el = root.get("{http://www.w3.org/XML/1998/namespace}lang")
            if lang_el:
                result["language"] = lang_el[:2]

        # RSS 2.0
        elif root.tag == "rss" or root.tag == "rdf":
            channel = root.find("channel")
            if channel is None:
                channel = root
            title_el = channel.find("title")
            if title_el is not None and title_el.text:
                result["title"] = title_el.text.strip()
            link_el = channel.find("link")
            if link_el is not None and link_el.text:
                result["site_url"] = link_el.text.strip()
            lang_el = channel.find("language")
            if lang_el is not None and lang_el.text:
                result["language"] = lang_el.text.strip()[:2]
    except ET.ParseError:
        pass

    return result


async def _enrich_feed_background(db: AsyncSession, feed_id: UUID, url: str) -> None:
    info = await try_autodiscover_feed_info(url)
    if not info:
        return
    result = await db.execute(select(Feed).where(Feed.id == feed_id))
    feed = result.scalar_one_or_none()
    if feed is None:
        return
    for key, val in info.items():
        if val and not getattr(feed, key):
            setattr(feed, key, val)
    await db.commit()


def _to_feed_response(feed: Feed, is_subscribed: bool, subscriber_count: int) -> FeedResponse:
    resp = FeedResponse.model_validate(feed)
    resp.is_subscribed = is_subscribed
    resp.subscriber_count = subscriber_count
    return resp


async def _compute_feed_extras(
    db: AsyncSession, feed_id: UUID, user_id: UUID
) -> tuple[bool, int]:
    """Return (is_subscribed, subscriber_count) for a single feed."""
    sub_count: int = (
        await db.scalar(
            select(func.count()).where(UserFeed.feed_id == feed_id)
        )
    ) or 0
    is_sub: bool = bool(
        await db.scalar(
            select(func.count()).where(
                UserFeed.feed_id == feed_id, UserFeed.user_id == user_id
            )
        )
    )
    return is_sub, sub_count


async def get_feeds(
    db: AsyncSession,
    user_id: UUID,
    category_id: UUID | None = None,
    subscribed_only: bool = False,
    page: int = 1,
    size: int = 20,
) -> Page[FeedResponse]:
    # Subqueries for extras
    sub_count_sq = (
        select(func.count(UserFeed.user_id))
        .where(UserFeed.feed_id == Feed.id)
        .correlate(Feed)
        .scalar_subquery()
    )
    is_sub_sq = (
        select(func.count())
        .where(UserFeed.feed_id == Feed.id, UserFeed.user_id == user_id)
        .correlate(Feed)
        .scalar_subquery()
    )

    stmt = select(Feed, is_sub_sq.label("is_subscribed"), sub_count_sq.label("sub_count"))

    if category_id is not None:
        stmt = stmt.where(Feed.category_id == category_id)
    if subscribed_only:
        stmt = stmt.where(
            select(UserFeed.feed_id)
            .where(UserFeed.feed_id == Feed.id, UserFeed.user_id == user_id)
            .exists()
        )

    total: int = (await db.scalar(select(func.count()).select_from(stmt.subquery()))) or 0

    stmt = stmt.order_by(Feed.created_at.desc()).offset((page - 1) * size).limit(size)
    rows = (await db.execute(stmt)).all()

    items = [
        _to_feed_response(feed, bool(is_sub), sub_count)
        for feed, is_sub, sub_count in rows
    ]
    import math
    return Page(items=items, total=total, page=page, pages=max(1, math.ceil(total / size)), size=size)


async def get_feed_by_id(
    db: AsyncSession, feed_id: UUID, user_id: UUID
) -> FeedResponse | None:
    result = await db.execute(select(Feed).where(Feed.id == feed_id))
    feed = result.scalar_one_or_none()
    if feed is None:
        return None
    is_sub, sub_count = await _compute_feed_extras(db, feed_id, user_id)
    return _to_feed_response(feed, is_sub, sub_count)


async def create_feed(db: AsyncSession, data: FeedCreate) -> FeedResponse:
    url_str = str(data.url)
    # Check for duplicate
    existing = await db.scalar(select(Feed).where(Feed.url == url_str))
    if existing is not None:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="Feed URL already exists")

    feed = Feed(
        url=url_str,
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        fetch_interval_min=data.fetch_interval_min,
        source_weight=data.source_weight,
        is_active=data.is_active,
    )
    db.add(feed)
    await db.commit()
    await db.refresh(feed)

    # Auto-discovery in background if title not provided
    if not data.title:
        asyncio.create_task(_enrich_feed_background(db, feed.id, url_str))

    return _to_feed_response(feed, False, 0)


async def update_feed(db: AsyncSession, feed_id: UUID, data: FeedUpdate) -> FeedResponse | None:
    result = await db.execute(select(Feed).where(Feed.id == feed_id))
    feed = result.scalar_one_or_none()
    if feed is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(feed, field, value)
    await db.commit()
    await db.refresh(feed)
    # subscriber_count is fine as 0 for admin update responses
    sub_count = (await db.scalar(select(func.count()).where(UserFeed.feed_id == feed_id))) or 0
    return _to_feed_response(feed, False, sub_count)


async def delete_feed(db: AsyncSession, feed_id: UUID) -> bool:
    result = await db.execute(select(Feed).where(Feed.id == feed_id))
    feed = result.scalar_one_or_none()
    if feed is None:
        return False
    # Soft delete (is_active = False) — hard delete will be considered in T05 when articles exist
    feed.is_active = False
    await db.commit()
    return True


async def subscribe(
    db: AsyncSession, user_id: UUID, feed_id: UUID, data: SubscriptionUpdate
) -> UserFeed:
    # Check feed exists
    feed = await db.scalar(select(Feed).where(Feed.id == feed_id))
    if feed is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Feed not found")

    # Check already subscribed
    existing = await db.scalar(
        select(UserFeed).where(UserFeed.user_id == user_id, UserFeed.feed_id == feed_id)
    )
    if existing is not None:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="Already subscribed")

    uf = UserFeed(
        user_id=user_id,
        feed_id=feed_id,
        custom_name=data.custom_name,
        notify_on_new=data.notify_on_new,
    )
    db.add(uf)
    await db.commit()
    return uf


async def unsubscribe(db: AsyncSession, user_id: UUID, feed_id: UUID) -> bool:
    result = await db.execute(
        select(UserFeed).where(UserFeed.user_id == user_id, UserFeed.feed_id == feed_id)
    )
    uf = result.scalar_one_or_none()
    if uf is None:
        return False
    await db.delete(uf)
    await db.commit()
    return True


async def get_user_feeds(db: AsyncSession, user_id: UUID) -> list[FeedResponse]:
    sub_count_sq = (
        select(func.count(UserFeed.user_id))
        .where(UserFeed.feed_id == Feed.id)
        .correlate(Feed)
        .scalar_subquery()
    )
    stmt = (
        select(Feed, UserFeed.custom_name, sub_count_sq.label("sub_count"))
        .join(UserFeed, (UserFeed.feed_id == Feed.id) & (UserFeed.user_id == user_id))
    )
    rows = (await db.execute(stmt)).all()
    result = []
    for feed, custom_name, sub_count in rows:
        resp = _to_feed_response(feed, True, sub_count)
        if custom_name:
            resp.title = custom_name
        result.append(resp)
    return result
