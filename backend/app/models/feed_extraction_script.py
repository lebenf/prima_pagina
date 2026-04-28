# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.types import SafeJSON


class FeedExtractionScript(Base):
    __tablename__ = "feed_extraction_scripts"

    feed_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("feeds.id", ondelete="CASCADE"), primary_key=True
    )
    selectors: Mapped[dict] = mapped_column(SafeJSON, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    validated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    success_rate: Mapped[float] = mapped_column(Float, default=1.0)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    sample_url: Mapped[str | None] = mapped_column(String(2048))
    sample_html_hash: Mapped[str | None] = mapped_column(String(64))

    feed: Mapped["Feed"] = relationship(back_populates="extraction_script")  # noqa: F821
