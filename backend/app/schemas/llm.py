# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class LLMConfigCreate(BaseModel):
    provider: Literal["ollama", "claude", "mistral", "hostyourai"]
    label: str | None = None
    model_name: str
    endpoint_url: str | None = None
    api_key: str | None = None
    is_active: bool = True
    timeout_sec: int = 300
    max_concurrent: int = 1
    tagging_language: str = "it"


class LLMConfigUpdate(BaseModel):
    label: str | None = None
    model_name: str | None = None
    endpoint_url: str | None = None
    api_key: str | None = None
    is_active: bool | None = None
    timeout_sec: int | None = None
    max_concurrent: int | None = None
    tagging_language: str | None = None


class LLMConfigResponse(BaseModel):
    id: uuid.UUID
    provider: str
    label: str | None
    model_name: str
    endpoint_url: str | None
    has_api_key: bool
    is_active: bool
    timeout_sec: int
    max_concurrent: int
    tagging_language: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthCheckResponse(BaseModel):
    ok: bool
    latency_ms: int
    error: str | None = None


class LLMFunctionAssignmentItem(BaseModel):
    function: str
    primary_config_id: uuid.UUID | None
    fallback_config_id: uuid.UUID | None


class LLMFunctionAssignmentUpdate(BaseModel):
    primary_config_id: uuid.UUID | None = None
    fallback_config_id: uuid.UUID | None = None
