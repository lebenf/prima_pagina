# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    q: str = Field(min_length=2, max_length=200)
    feed_id: UUID | None = None
    category_id: UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=50)


class SearchResultItem(BaseModel):
    id: UUID
    feed_id: UUID
    feed_title: str | None
    title: str | None
    title_highlighted: str | None
    excerpt_snippet: str | None
    url: str | None
    published_at: datetime | None
    language: str | None
    tags: list[str]
    is_read: bool
    is_starred: bool
    user_vote: int


class SearchResponse(BaseModel):
    items: list[SearchResultItem]
    total: int
    page: int
    pages: int
    query: str
