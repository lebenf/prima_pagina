# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.types import SafeJSON


class EventStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class TitleSource(str, Enum):
    REPRESENTATIVE = "representative"
    LLM = "llm"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    title_source: Mapped[str] = mapped_column(String(20), default=TitleSource.REPRESENTATIVE.value)
    synopsis: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(SafeJSON, default=list)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default=EventStatus.OPEN.value)
    article_count: Mapped[int] = mapped_column(Integer, default=1)
    source_count: Mapped[int] = mapped_column(Integer, default=1)
    opened_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    last_activity_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    category: Mapped["Category | None"] = relationship()  # noqa: F821
    articles: Mapped[list["Article"]] = relationship(back_populates="event")  # noqa: F821
