# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from datetime import datetime

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FrontPageCache(Base):
    __tablename__ = "frontpage_cache"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        index=True, nullable=True
    )
    # Memorizza la risposta strutturata della frontpage
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    # Flag per indicare se la cache è valida
    is_valid: Mapped[bool] = mapped_column(default=True)
    # Tipo: 'articles' o 'events'
    cache_type: Mapped[str] = mapped_column(String(20), default="articles")
