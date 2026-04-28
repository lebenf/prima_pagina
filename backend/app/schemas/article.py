# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ArticleListItem(BaseModel):
    id: UUID
    feed_id: UUID
    feed_title: str | None
    title: str | None
    url: str | None
    author: str | None
    content_excerpt: str | None
    language: str | None
    tags: list[str]
    published_at: datetime | None
    fetched_at: datetime
    # User state — None when no ArticleUserState row exists for this user
    is_read: bool = False
    is_starred: bool = False
    is_archived: bool = False
    user_vote: int = 0

    model_config = ConfigDict(from_attributes=True)


class ArticleDetail(ArticleListItem):
    content_fulltext: str | None
    fulltext_status: str  # "pending" | "ok" | "failed" | "blocked"
    fulltext_loading: bool  # True while background fetch is in progress
    tags_source: str


class ArticleStateUpdate(BaseModel):
    is_read: bool | None = None
    is_starred: bool | None = None
    is_archived: bool | None = None


class ArticleStateResponse(BaseModel):
    user_id: UUID
    article_id: UUID
    is_read: bool
    is_starred: bool
    is_archived: bool
    read_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class FrontPageColumn(BaseModel):
    category_slug: str
    category_name: str
    articles: list[ArticleListItem]


class FrontPageResponse(BaseModel):
    hero: ArticleListItem | None
    second_row: list[ArticleListItem]
    columns: list[FrontPageColumn]
    digest_available: bool
    digest_id: UUID | None


class ArticleListResponse(BaseModel):
    items: list[ArticleListItem]
    total: int
    page: int
    pages: int
    unread_count: int


class FulltextStatusResponse(BaseModel):
    status: str
    fulltext_available: bool


class MarkReadRequest(BaseModel):
    feed_id: UUID
    before: datetime | None = None
