import asyncio
import logging
import uuid as _uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plugin_config import PluginConfig
from app.plugins.base import NotificationEvent, NotificationPayload, NotificationPlugin
from app.plugins.telegram import TelegramPlugin

logger = logging.getLogger(__name__)

PLUGIN_REGISTRY: dict[str, type[NotificationPlugin]] = {
    "telegram": TelegramPlugin,
}

PLUGIN_LABELS = {
    "telegram": "Telegram",
}

PLUGIN_DESCRIPTIONS = {
    "telegram": "Invia notifiche tramite un bot Telegram a una chat, gruppo o canale.",
}


class PluginManager:
    async def dispatch(
        self,
        event: NotificationEvent,
        payload: NotificationPayload,
        db: AsyncSession,
    ) -> None:
        configs = await self._load_active_configs(db, payload.user_id)

        tasks = []
        for config in configs:
            plugin_class = PLUGIN_REGISTRY.get(config.plugin_type)
            if not plugin_class:
                logger.warning("plugin type not found: %s", config.plugin_type)
                continue
            plugin = plugin_class(config)
            tasks.append(self._send_safe(plugin, payload))

        if tasks:
            await asyncio.gather(*tasks)

    async def _send_safe(self, plugin: NotificationPlugin, payload: NotificationPayload) -> None:
        try:
            success = await plugin.send(payload)
            if not success:
                logger.warning("plugin %s: send returned False", plugin.plugin_type)
        except Exception as e:
            logger.error("plugin %s: unexpected error: %s", plugin.plugin_type, e, exc_info=True)

    async def _load_active_configs(
        self,
        db: AsyncSession,
        user_id: str | None,
    ) -> list[PluginConfig]:
        uid: _uuid.UUID | None = None
        if user_id is not None:
            try:
                uid = _uuid.UUID(str(user_id))
            except (ValueError, AttributeError):
                uid = None

        stmt = select(PluginConfig).where(
            PluginConfig.is_active == True,  # noqa: E712
            or_(
                PluginConfig.user_id.is_(None),
                PluginConfig.user_id == uid,
            ),
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


plugin_manager = PluginManager()
