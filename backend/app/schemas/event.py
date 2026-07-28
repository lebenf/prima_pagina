# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.article import ArticleListItem


class EventListItem(BaseModel):
    id: UUID
    title: str
    title_source: str
    synopsis: str | None
    tags: list[str]
    category_id: UUID | None
    category_name: str | None
    status: str
    article_count: int
    source_count: int
    opened_at: datetime
    last_activity_at: datetime
    user_vote: int = 0

    model_config = ConfigDict(from_attributes=True)


class EventDetail(EventListItem):
    articles: list[ArticleListItem]


class EventFrontPageColumn(BaseModel):
    category_slug: str
    category_name: str
    events: list[EventListItem]


class EventFrontPageResponse(BaseModel):
    hero: EventListItem | None
    second_row: list[EventListItem]
    columns: list[EventFrontPageColumn]
    digest_available: bool = False
    digest_id: UUID | None = None


class EventListResponse(BaseModel):
    items: list[EventListItem]
    total: int
    page: int
    pages: int


class EventVoteResponse(BaseModel):
    event_id: UUID
    vote: int
    topic_scores_updated: list[str]


class MergeEventsRequest(BaseModel):
    target_event_id: UUID
