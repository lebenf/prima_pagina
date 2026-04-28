# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Digest(Base):
    __tablename__ = "digests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str | None] = mapped_column(String(500))
    period_start: Mapped[datetime] = mapped_column(nullable=False)
    period_end: Mapped[datetime] = mapped_column(nullable=False)
    content_html: Mapped[str | None] = mapped_column(Text)
    content_text: Mapped[str | None] = mapped_column(Text)
    virtual_feed_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("virtual_feeds.id", ondelete="SET NULL"), nullable=True
    )
    llm_provider: Mapped[str | None] = mapped_column(String(50))
    llm_model: Mapped[str | None] = mapped_column(String(100))
    article_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="ok")
    generation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user: Mapped["User | None"] = relationship()  # noqa: F821
    virtual_feed: Mapped["VirtualFeed | None"] = relationship(back_populates="digests")  # noqa: F821
