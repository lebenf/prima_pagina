import uuid
from datetime import datetime

from cryptography.fernet import Fernet
from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LLMConfig(Base):
    __tablename__ = "llm_configs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str | None] = mapped_column(String(100))
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    endpoint_url: Mapped[str | None] = mapped_column(String(2048))
    api_key_encrypted: Mapped[str | None] = mapped_column(Text)
    use_for: Mapped[list] = mapped_column(JSON, default=lambda: ["tagging", "digest"])
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    def set_api_key(self, plain: str, fernet_key: str) -> None:
        f = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)
        self.api_key_encrypted = f.encrypt(plain.encode()).decode()

    def get_api_key(self, fernet_key: str) -> str | None:
        if not self.api_key_encrypted:
            return None
        f = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)
        return f.decrypt(self.api_key_encrypted.encode()).decode()
