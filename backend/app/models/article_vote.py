# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ArticleVote(Base):
    __tablename__ = "article_votes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True
    )
    vote: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    voted_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user: Mapped["User"] = relationship()  # noqa: F821
    article: Mapped["Article"] = relationship()  # noqa: F821
