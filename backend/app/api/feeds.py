# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.database import get_db
from app.models.feed import Feed
from app.models.user import User
from app.schemas.common import Page
from app.schemas.extraction import ExtractionScriptResponse
from app.schemas.feed import FeedCreate, FeedResponse, FeedUpdate, SubscriptionUpdate
from app.services import feed_service

router = APIRouter(tags=["feeds"])


@router.get("/feeds/subscribed", response_model=list[FeedResponse])
async def get_subscribed_feeds(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await feed_service.get_user_feeds(db, current_user.id)


@router.get("/feeds", response_model=Page[FeedResponse])
async def list_feeds(
    category_id: uuid.UUID | None = Query(default=None),
    subscribed: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await feed_service.get_feeds(
        db,
        user_id=current_user.id,
        category_id=category_id,
        subscribed_only=subscribed,
        page=page,
        size=size,
    )


@router.post("/feeds/discover")
async def discover_feed(
    body: dict,
    _: User = Depends(get_current_user),
):
    """Auto-discover feed title and metadata from a URL."""
    url = body.get("url", "")
    if not url:
        raise HTTPException(status_code=422, detail="url required")
    feed_service.validate_feed_url(url)
    info = await feed_service.try_autodiscover_feed_info(url)
    return {"title": info.get("title", ""), "description": info.get("description")}


@router.post("/feeds", response_model=FeedResponse, status_code=status.HTTP_201_CREATED)
async def create_feed(
    body: FeedCreate,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await feed_service.create_feed(db, body)


@router.get("/feeds/{feed_id}", response_model=FeedResponse)
async def get_feed(
    feed_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    feed = await feed_service.get_feed_by_id(db, feed_id, current_user.id)
    if feed is None:
        raise HTTPException(status_code=404, detail="Feed not found")
    return feed


@router.put("/feeds/{feed_id}", response_model=FeedResponse)
async def update_feed(
    feed_id: uuid.UUID,
    body: FeedUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    feed = await feed_service.update_feed(db, feed_id, body, current_user.id)
    if feed is None:
        raise HTTPException(status_code=404, detail="Feed not found")
    return feed


@router.delete("/feeds/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feed(
    feed_id: uuid.UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    ok = await feed_service.delete_feed(db, feed_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Feed not found")


@router.post("/feeds/{feed_id}/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe_feed(
    feed_id: uuid.UUID,
    body: SubscriptionUpdate = SubscriptionUpdate(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await feed_service.subscribe(db, current_user.id, feed_id, body)
    return {"detail": "Subscribed"}


@router.delete("/feeds/{feed_id}/subscribe", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe_feed(
    feed_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await feed_service.unsubscribe(db, current_user.id, feed_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Not subscribed to this feed")


@router.get("/feeds/{feed_id}/extraction-script", response_model=ExtractionScriptResponse)
async def get_extraction_script(
    feed_id: uuid.UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.feed_extraction_script import FeedExtractionScript
    script = await db.get(FeedExtractionScript, feed_id)
    if script is None:
        raise HTTPException(status_code=404, detail="No extraction script for this feed")
    return script


@router.post(
    "/feeds/{feed_id}/extraction-script/regenerate",
    status_code=status.HTTP_202_ACCEPTED,
)
async def regenerate_extraction_script(
    feed_id: uuid.UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select as sa_select
    from app.models.article import Article
    from app.models.feed_extraction_script import FeedExtractionScript

    feed = await db.get(Feed, feed_id)
    if feed is None:
        raise HTTPException(status_code=404, detail="Feed not found")

    # Find a recent article URL to use as sample
    row = await db.execute(
        sa_select(Article.url)
        .where(Article.feed_id == feed_id, Article.url.is_not(None))
        .order_by(Article.published_at.desc())
        .limit(1)
    )
    sample_url = row.scalar_one_or_none()
    if sample_url is None:
        raise HTTPException(
            status_code=422,
            detail="No article URL available for script generation",
        )

    # Invalidate current script
    existing = await db.get(FeedExtractionScript, feed_id)
    if existing:
        existing.is_active = False
        await db.commit()

    async def _regen():
        from app.services.full_text import _try_generate_script_for_feed
        await _try_generate_script_for_feed(feed_id, sample_url)

    asyncio.create_task(_regen())
    return {"message": "Rigenerazione avviata"}


@router.post("/feeds/{feed_id}/refresh", status_code=status.HTTP_202_ACCEPTED)
async def refresh_feed(
    feed_id: uuid.UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Feed).where(Feed.id == feed_id))
    feed = result.scalar_one_or_none()
    if feed is None:
        raise HTTPException(status_code=404, detail="Feed not found")

    async def _do_refresh():
        from app.database import AsyncSessionLocal
        from app.services.feed_fetcher import fetch_feed
        async with AsyncSessionLocal() as session:
            await fetch_feed(feed_id, session)

    asyncio.create_task(_do_refresh())
    return {"detail": "Refresh enqueued"}
