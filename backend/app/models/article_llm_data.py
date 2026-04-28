# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.types import SafeJSON


class ArticleLLMData(Base):
    __tablename__ = "article_llm_data"

    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True
    )
    summary: Mapped[str | None] = mapped_column(Text)
    related_article_ids: Mapped[list] = mapped_column(SafeJSON, default=list)
    computed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    article: Mapped["Article"] = relationship(back_populates="llm_data")  # noqa: F821
