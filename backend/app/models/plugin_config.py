# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PluginConfig(Base):
    __tablename__ = "plugin_configs"
    __table_args__ = (
        Index("ix_plugin_configs_user_id", "user_id"),
        Index("ix_plugin_configs_plugin_type", "plugin_type"),
        Index("ix_plugin_configs_is_active", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plugin_type: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str | None] = mapped_column(String(100))
    config_json_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user: Mapped["User | None"] = relationship()  # noqa: F821

    def set_config(self, config: dict) -> None:
        from cryptography.fernet import Fernet
        from app.config import get_settings
        key = get_settings().encryption_key
        f = Fernet(key.encode() if isinstance(key, str) else key)
        self.config_json_encrypted = f.encrypt(json.dumps(config).encode()).decode()

    def get_config(self) -> dict:
        from cryptography.fernet import Fernet
        from app.config import get_settings
        key = get_settings().encryption_key
        f = Fernet(key.encode() if isinstance(key, str) else key)
        return json.loads(f.decrypt(self.config_json_encrypted.encode()).decode())
