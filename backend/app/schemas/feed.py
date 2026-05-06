# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from app.schemas.extraction import ExtractionScriptResponse


class FeedCreate(BaseModel):
    url: AnyHttpUrl
    title: str | None = None
    description: str | None = None
    category_id: UUID | None = None
    fetch_interval_min: int = Field(default=60, ge=5, le=1440)
    source_weight: float = Field(default=1.0, ge=0.1, le=5.0)
    is_active: bool = True
    fulltext_enabled: bool = False
    fulltext_mode: str = "trafilatura"
    fulltext_include_images: bool = False


class FeedUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category_id: UUID | None = None
    fetch_interval_min: int | None = Field(default=None, ge=5, le=1440)
    source_weight: float | None = Field(default=None, ge=0.1, le=5.0)
    is_active: bool | None = None
    fulltext_enabled: bool | None = None
    fulltext_mode: str | None = None
    fulltext_include_images: bool | None = None


class FeedResponse(BaseModel):
    id: UUID
    url: str
    title: str | None
    description: str | None
    site_url: str | None
    favicon_url: str | None
    category_id: UUID | None
    language: str | None
    fetch_interval_min: int
    last_fetched_at: datetime | None
    last_status: int | None
    error_count: int
    is_active: bool
    source_weight: float
    fulltext_enabled: bool = False
    fulltext_mode: str = "trafilatura"
    fulltext_include_images: bool = False
    extraction_script: ExtractionScriptResponse | None = None
    created_at: datetime
    is_subscribed: bool = False
    subscriber_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class SubscriptionUpdate(BaseModel):
    custom_name: str | None = None
    notify_on_new: bool = False
