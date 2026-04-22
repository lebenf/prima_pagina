from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.plugin_config import PluginConfig


class NotificationEvent(str, Enum):
    NEW_ARTICLE = "new_article"
    DIGEST_READY = "digest_ready"
    FEED_ERROR = "feed_error"
    SYSTEM = "system"


@dataclass
class NotificationPayload:
    event: NotificationEvent
    user_id: str | None
    title: str
    body: str
    body_html: str | None = None
    url: str | None = None
    metadata: dict | None = field(default=None)


class NotificationPlugin(ABC):
    plugin_type: str = ""
    config_schema: dict = {}

    def __init__(self, config: "PluginConfig"):
        self.config = config
        self._cfg = config.get_config()

    @abstractmethod
    async def send(self, payload: NotificationPayload) -> bool:
        """Send notification. Returns True on success, False on handled failure. Never raises."""
        ...

    @abstractmethod
    async def test_connection(self) -> tuple[bool, str]:
        """Check config and reachability. Returns (ok, message)."""
        ...

    @classmethod
    def validate_config(cls, config: dict) -> list[str]:
        errors = []
        for field_name, meta in cls.config_schema.items():
            if meta.get("required") and field_name not in config:
                errors.append(f"Campo obbligatorio mancante: {field_name}")
        return errors
