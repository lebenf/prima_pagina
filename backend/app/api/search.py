# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.config import Settings, get_settings
from app.models.user import User
from app.schemas.search import SearchFilters, SearchResponse
from app.services.search_service import search_articles

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(min_length=2, max_length=200),
    feed_id: UUID | None = None,
    category_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SearchResponse:
    dialect = "postgresql" if "postgresql" in settings.database_url else "sqlite"
    filters = SearchFilters(
        q=q,
        feed_id=feed_id,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
    )
    return await search_articles(db, current_user.id, filters, db_dialect=dialect)
