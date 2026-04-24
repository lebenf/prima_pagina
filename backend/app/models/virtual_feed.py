# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.types import SafeJSON


class FilterType(str, Enum):
    CATEGORY = "category"
    TAGS = "tags"
    MIXED = "mixed"


class VirtualFeed(Base):
    __tablename__ = "virtual_feeds"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    filter_type: Mapped[str] = mapped_column(String(20), nullable=False)
    filter_config: Mapped[dict] = mapped_column(SafeJSON, nullable=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    rss_token: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4, unique=True)
    include_digest: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship()  # noqa: F821
    digests: Mapped[list["Digest"]] = relationship(back_populates="virtual_feed")  # noqa: F821
