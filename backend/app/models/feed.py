# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Feed(Base):
    __tablename__ = "feeds"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    site_url: Mapped[str | None] = mapped_column(String(2048))
    favicon_url: Mapped[str | None] = mapped_column(String(2048))
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    language: Mapped[str | None] = mapped_column(String(10))
    fetch_interval_min: Mapped[int] = mapped_column(Integer, default=60)
    last_fetched_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_etag: Mapped[str | None] = mapped_column(String(500))
    last_modified: Mapped[str | None] = mapped_column(String(100))
    last_status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_global: Mapped[bool] = mapped_column(Boolean, default=True)
    source_weight: Mapped[float] = mapped_column(Float, default=1.0)
    fulltext_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    fulltext_mode: Mapped[str] = mapped_column(String(20), default="trafilatura")
    fulltext_include_images: Mapped[bool] = mapped_column(Boolean, default=False)
    # Set by error backoff to delay next fetch; None = use regular fetch_interval_min schedule
    next_fetch_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    category: Mapped["Category | None"] = relationship(  # noqa: F821
        back_populates="feeds",
    )
    subscriptions: Mapped[list["UserFeed"]] = relationship(  # noqa: F821
        back_populates="feed",
        cascade="all, delete-orphan",
    )
    articles: Mapped[list["Article"]] = relationship(  # noqa: F821
        back_populates="feed", cascade="all, delete-orphan"
    )
    extraction_script: Mapped["FeedExtractionScript | None"] = relationship(  # noqa: F821
        back_populates="feed", uselist=False, cascade="all, delete-orphan"
    )
