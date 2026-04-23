# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9-]+$", max_length=100)
    name: dict[str, str]  # {"it": "...", "en": "...", ...}
    parent_id: UUID | None = None


class CategoryUpdate(BaseModel):
    name: dict[str, str] | None = None
    parent_id: UUID | None = None


class CategoryResponse(BaseModel):
    id: UUID
    slug: str
    name: dict[str, str]
    parent_id: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryResponseLocalized(BaseModel):
    """Category with name already resolved to the requested language."""

    id: UUID
    slug: str
    name: str  # already translated
    parent_id: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
