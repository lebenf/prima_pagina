# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExtractionScriptResponse(BaseModel):
    feed_id: UUID
    selectors: dict
    generated_at: datetime
    validated_at: datetime | None
    is_active: bool
    success_rate: float
    consecutive_failures: int
    sample_url: str | None

    model_config = ConfigDict(from_attributes=True)
