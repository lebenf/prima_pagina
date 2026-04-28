# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserTopicPreference(Base):
    __tablename__ = "user_topic_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    tag: Mapped[str] = mapped_column(String(100), primary_key=True)
    score: Mapped[float] = mapped_column(default=0.0)
    vote_count: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship()  # noqa: F821
