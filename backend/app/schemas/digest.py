# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DigestResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    period_start: datetime
    period_end: datetime
    content_html: str | None
    content_text: str | None
    virtual_feed_id: uuid.UUID | None
    llm_provider: str | None
    llm_model: str | None
    article_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DigestGenerateOptions(BaseModel):
    period_start: datetime | None = None
    period_end: datetime | None = None
    virtual_feed_id: uuid.UUID | None = None
    category_ids: list[uuid.UUID] = Field(default_factory=list)
    max_articles: int = Field(default=30, ge=5, le=100)
    force_fulltext: bool = True
    llm_config_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def set_defaults(self) -> "DigestGenerateOptions":
        now = datetime.utcnow()
        if self.period_end is None:
            self.period_end = now
        if self.period_start is None:
            self.period_start = now - timedelta(hours=24)
        if self.period_start >= self.period_end:
            raise ValueError("period_start must be before period_end")
        return self


class DigestListResponse(BaseModel):
    items: list[DigestResponse]
    total: int
    page: int
    pages: int
