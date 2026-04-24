# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.types import SafeJSON


class FulltextStatus(str, Enum):
    PENDING = "pending"
    OK = "ok"
    FAILED = "failed"
    BLOCKED = "blocked"


class TagsSource(str, Enum):
    NONE = "none"
    MANUAL = "manual"
    LLM = "llm"


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint("feed_id", "guid", name="uq_article_feed_guid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    feed_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("feeds.id", ondelete="CASCADE"), nullable=False
    )
    guid: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str | None] = mapped_column(String(1000))
    url: Mapped[str | None] = mapped_column(String(2048))
    author: Mapped[str | None] = mapped_column(String(500))
    content_excerpt: Mapped[str | None] = mapped_column(Text)
    content_fulltext: Mapped[str | None] = mapped_column(Text)
    fulltext_fetched_at: Mapped[datetime | None] = mapped_column(nullable=True)
    fulltext_status: Mapped[str] = mapped_column(
        String(20), default=FulltextStatus.PENDING.value
    )
    language: Mapped[str | None] = mapped_column(String(10))
    tags: Mapped[list] = mapped_column(SafeJSON, default=list)
    tags_source: Mapped[str] = mapped_column(String(20), default=TagsSource.NONE.value)
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    feed: Mapped["Feed"] = relationship(back_populates="articles")  # noqa: F821
    user_states: Mapped[list["ArticleUserState"]] = relationship(  # noqa: F821
        back_populates="article", cascade="all, delete-orphan"
    )
