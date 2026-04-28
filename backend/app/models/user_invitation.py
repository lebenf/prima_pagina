# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from datetime import datetime, timedelta

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserInvitation(Base):
    __tablename__ = "user_invitations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    token: Mapped[uuid.UUID] = mapped_column(unique=True, default=uuid.uuid4)
    email: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.utcnow() + timedelta(days=7)
    )
    used_at: Mapped[datetime | None]
    used_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    creator: Mapped["User"] = relationship(foreign_keys=[created_by])  # noqa: F821
    registrant: Mapped["User | None"] = relationship(foreign_keys=[used_by])  # noqa: F821

    @property
    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > datetime.utcnow()
