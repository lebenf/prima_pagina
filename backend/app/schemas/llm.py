import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class LLMConfigCreate(BaseModel):
    provider: Literal["ollama", "claude"]
    label: str | None = None
    model_name: str
    endpoint_url: str | None = None
    api_key: str | None = None
    use_for: list[Literal["tagging", "digest"]] = ["tagging", "digest"]
    is_default: bool = False
    is_active: bool = True
    priority: int = 0


class LLMConfigUpdate(BaseModel):
    label: str | None = None
    model_name: str | None = None
    endpoint_url: str | None = None
    api_key: str | None = None
    use_for: list[Literal["tagging", "digest"]] | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    priority: int | None = None


class LLMConfigResponse(BaseModel):
    id: uuid.UUID
    provider: str
    label: str | None
    model_name: str
    endpoint_url: str | None
    has_api_key: bool
    use_for: list[str]
    is_default: bool
    is_active: bool
    priority: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthCheckResponse(BaseModel):
    ok: bool
    latency_ms: int
    error: str | None = None
