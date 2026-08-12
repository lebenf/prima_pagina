# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.article import ArticleListItem
from app.schemas.event import EventDetail, EventFrontPageResponse, EventListResponse, EventVoteResponse
from app.schemas.vote import VoteRequest
from app.services import event_service, event_vote_service

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/frontpage", response_model=EventFrontPageResponse)
async def get_frontpage(
    lang: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    effective_lang = lang or current_user.preferred_lang or "it"
    return await event_service.get_frontpage_events_cached(db, current_user.id, effective_lang)


@router.get("", response_model=EventListResponse)
async def list_events(
    category_id: UUID | None = None,
    status: str | None = Query(default=None, pattern="^(open|closed)$"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    lang: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    effective_lang = lang or current_user.preferred_lang or "it"
    return await event_service.list_events(
        db, current_user.id, effective_lang, page=page, size=size,
        category_id=category_id, status=status,
    )


@router.get("/{event_id}", response_model=EventDetail)
async def get_event(
    event_id: UUID,
    lang: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    effective_lang = lang or current_user.preferred_lang or "it"
    detail = await event_service.get_event_detail(db, event_id, current_user.id, effective_lang)
    if detail is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return detail


@router.get("/{event_id}/articles", response_model=list[ArticleListItem])
async def get_event_articles(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    articles = await event_service.get_event_articles(db, event_id, current_user.id)
    if articles is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return articles


@router.post("/{event_id}/vote", response_model=EventVoteResponse)
async def cast_vote(
    event_id: UUID,
    body: VoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await event_vote_service.cast_vote(db, current_user.id, event_id, body.vote)


@router.delete("/{event_id}/vote", response_model=EventVoteResponse)
async def remove_vote(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await event_vote_service.remove_vote(db, current_user.id, event_id)
