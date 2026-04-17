from functools import lru_cache
from typing import Literal

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

    # CORS
    allowed_origins: list[str] = ["http://localhost:5173"]

    # Scheduler
    feed_default_interval_min: int = 60
    digest_cron: str = "0 7 * * *"

    # LLM
    ollama_endpoint: str = "http://localhost:11434"
    anthropic_api_key: str = ""

    # Initial admin (optional)
    admin_email: str | None = None
    admin_username: str | None = None
    admin_password: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
