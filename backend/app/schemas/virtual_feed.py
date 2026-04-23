# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class VirtualFeedCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    filter_type: Literal["category", "tags", "mixed"]
    filter_config: dict
    is_shared: bool = False
    include_digest: bool = False

    @model_validator(mode="after")
    def validate_filter_config(self):
        fc = self.filter_config or {}
        ft = self.filter_type
        if ft == "category":
            if "category_id" not in fc:
                raise ValueError("filter_config must contain 'category_id' for category filter")
        elif ft == "tags":
            tags = fc.get("tags", [])
            if not tags or not isinstance(tags, list):
                raise ValueError("filter_config must contain non-empty 'tags' list for tags filter")
            op = fc.get("operator", "OR")
            if op not in ("AND", "OR"):
                raise ValueError("operator must be 'AND' or 'OR'")
        elif ft == "mixed":
            cats = fc.get("categories", [])
            tags = fc.get("tags", [])
            if not cats and not tags:
                raise ValueError("filter_config must contain 'categories' or 'tags' for mixed filter")
            op = fc.get("operator", "OR")
            if op not in ("AND", "OR"):
                raise ValueError("operator must be 'AND' or 'OR'")
        return self


class VirtualFeedUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = None
    filter_type: Literal["category", "tags", "mixed"] | None = None
    filter_config: dict | None = None
    is_shared: bool | None = None
    include_digest: bool | None = None


class VirtualFeedResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: str | None
    filter_type: str
    filter_config: dict
    is_shared: bool
    rss_token: uuid.UUID
    include_digest: bool
    rss_url: str
    article_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    rss_token: uuid.UUID
    rss_url: str


class FilterPreviewRequest(BaseModel):
    filter_type: Literal["category", "tags", "mixed"]
    filter_config: dict
