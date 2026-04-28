# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.article import Article
from app.models.article_user_state import ArticleUserState
from app.models.user import User
from app.schemas.article import (
    ArticleDetail,
    ArticleListItem,
    ArticleListResponse,
    ArticleStateResponse,
    ArticleStateUpdate,
    FrontPageResponse,
    FulltextStatusResponse,
    MarkReadRequest,
)
from app.schemas.vote import VoteRequest, VoteResponse
from app.services import article_service
from app.services import vote_service

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("/frontpage", response_model=FrontPageResponse)
async def get_frontpage(
    lang: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    effective_lang = lang or current_user.preferred_lang or "it"
    return await article_service.get_frontpage_articles(db, current_user.id, effective_lang)


@router.get("", response_model=ArticleListResponse)
async def list_articles(
    feed_id: UUID | None = None,
    category_id: UUID | None = None,
    tags: Annotated[list[str] | None, Query()] = None,
    is_read: bool | None = None,
    is_starred: bool | None = None,
    is_archived: bool | None = None,
    subscribed_only: bool = True,
    search: str | None = Query(default=None, min_length=3),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    order_by: str = Query(default="published_at", pattern="^(published_at|fetched_at)$"),
    order_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await article_service.get_articles(
        db=db,
        user_id=current_user.id,
        feed_id=feed_id,
        category_id=category_id,
        tags=tags,
        is_read=is_read,
        is_starred=is_starred,
        is_archived=is_archived,
        subscribed_only=subscribed_only,
        search=search,
        page=page,
        size=size,
        order_by=order_by,  # type: ignore[arg-type]
        order_dir=order_dir,  # type: ignore[arg-type]
    )


@router.get("/{article_id}", response_model=ArticleDetail)
async def get_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    detail = await article_service.get_article_detail(db, article_id, current_user.id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return detail


@router.patch("/{article_id}/state", response_model=ArticleStateResponse)
async def update_article_state(
    article_id: UUID,
    body: ArticleStateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await article_service.update_article_state(db, article_id, current_user.id, body)


@router.post("/mark-read", response_model=dict)
async def mark_feed_read(
    body: MarkReadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = await article_service.mark_feed_read(
        db, body.feed_id, current_user.id, body.before
    )
    return {"count": count}


@router.post("/{article_id}/vote", response_model=VoteResponse)
async def cast_vote(
    article_id: UUID,
    body: VoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await vote_service.cast_vote(db, current_user.id, article_id, body.vote)


@router.delete("/{article_id}/vote", response_model=VoteResponse)
async def remove_vote(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await vote_service.remove_vote(db, current_user.id, article_id)


@router.get("/{article_id}/related", response_model=list[ArticleListItem])
async def get_related_articles(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import select, and_
    from sqlalchemy.orm import selectinload
    from app.models.article_llm_data import ArticleLLMData

    article = await db.get(
        Article, article_id,
        options=[selectinload(Article.llm_data)]
    )
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    llm_data: ArticleLLMData | None = article.llm_data
    if not llm_data or not llm_data.related_article_ids:
        return []

    related_ids = [UUID(id_str) for id_str in llm_data.related_article_ids]

    from app.models.feed import Feed
    result = await db.execute(
        select(Article, Feed.title.label("feed_title"), ArticleUserState)
        .join(Feed, Article.feed_id == Feed.id)
        .outerjoin(
            ArticleUserState,
            and_(
                ArticleUserState.article_id == Article.id,
                ArticleUserState.user_id == current_user.id,
            ),
        )
        .where(Article.id.in_(related_ids))
    )
    rows = result.all()

    articles_map = {
        row.Article.id: (row.Article, row.feed_title, row.ArticleUserState)
        for row in rows
    }

    from app.services.article_service import _build_list_item
    ordered = [
        _build_list_item(articles_map[rid][0], articles_map[rid][1], articles_map[rid][2])
        for rid in related_ids
        if rid in articles_map
    ]
    return ordered


@router.get("/{article_id}/fulltext-status", response_model=FulltextStatusResponse)
async def get_fulltext_status(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.article import Article, FulltextStatus
    from app.services.full_text import is_fetch_active

    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")

    return FulltextStatusResponse(
        status=article.fulltext_status,
        fulltext_available=(
            article.fulltext_status == FulltextStatus.OK.value
            and article.content_fulltext is not None
        ),
    )
