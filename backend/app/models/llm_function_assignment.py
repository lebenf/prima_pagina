# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LLMFunction(str, Enum):
    TAGGING = "tagging"
    EVENT_SUMMARY = "event_summary"
    EXTRACTION_SCRIPT = "extraction_script"
    RELATED_ARTICLES = "related_articles"
    DIGEST = "digest"


class LLMFunctionAssignment(Base):
    __tablename__ = "llm_function_assignments"

    function: Mapped[str] = mapped_column(String(30), primary_key=True)
    primary_config_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("llm_configs.id", ondelete="SET NULL"), nullable=True
    )
    fallback_config_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("llm_configs.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    primary_config: Mapped["LLMConfig | None"] = relationship(foreign_keys=[primary_config_id])  # noqa: F821
    fallback_config: Mapped["LLMConfig | None"] = relationship(foreign_keys=[fallback_config_id])  # noqa: F821
