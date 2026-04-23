# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_env: Literal["development", "production"] = "development"
    log_level: str = "INFO"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/prima_pagina.db"

    # Security
    secret_key: str
    encryption_key: str
    session_max_age_days: int = 30
    secure_cookies: bool = False

    # CORS — accepts JSON array or comma-separated string in .env
    allowed_origins: list[str] = ["http://localhost:5173"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: object) -> object:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    # Scheduler
    feed_default_interval_min: int = 60
    digest_cron: str = "0 7 * * *"

    # LLM
    ollama_endpoint: str = "http://localhost:11434"
    anthropic_api_key: str = ""

    # Notifications
    app_base_url: str = "http://localhost:5173"

    # Initial admin (optional)
    admin_email: str | None = None
    admin_username: str | None = None
    admin_password: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
