"""Tests for plugin system base + manager."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.plugin_config import PluginConfig
from app.plugins.base import NotificationEvent, NotificationPayload
from app.plugins.manager import PLUGIN_REGISTRY, PluginManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_plugin_config(plugin_type: str = "telegram", is_active: bool = True, user_id=None) -> PluginConfig:
    cfg = PluginConfig(
        plugin_type=plugin_type,
        is_active=is_active,
        user_id=user_id,
        config_json_encrypted="",
    )
    cfg.id = uuid.uuid4()
    cfg.set_config({
        "bot_token": "test-token",
        "chat_id": "123456",
        "notify_events": ["new_article", "digest_ready"],
    })
    return cfg


def _make_payload(event=NotificationEvent.NEW_ARTICLE, user_id="user-1") -> NotificationPayload:
    return NotificationPayload(
        event=event,
        user_id=user_id,
        title="Test Article",
        body="Test body text",
        url="https://example.com/article",
    )


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------

def test_plugin_registry_contains_telegram():
    assert "telegram" in PLUGIN_REGISTRY


def test_validate_config_missing_required():
    from app.plugins.telegram import TelegramPlugin
    errors = TelegramPlugin.validate_config({})
    assert any("bot_token" in e for e in errors)
    assert any("chat_id" in e for e in errors)


def test_validate_config_ok():
    from app.plugins.telegram import TelegramPlugin
    errors = TelegramPlugin.validate_config({"bot_token": "tok", "chat_id": "123"})
    assert errors == []


def test_validate_config_missing_one_field():
    from app.plugins.telegram import TelegramPlugin
    errors = TelegramPlugin.validate_config({"bot_token": "tok"})
    assert len(errors) == 1
    assert "chat_id" in errors[0]


# ---------------------------------------------------------------------------
# PluginManager dispatch tests
# ---------------------------------------------------------------------------

async def test_plugin_manager_dispatch(db_session):
    cfg = _make_plugin_config()
    db_session.add(cfg)
    await db_session.commit()

    payload = _make_payload()
    manager = PluginManager()

    with patch("app.plugins.telegram.TelegramPlugin.send", new_callable=AsyncMock, return_value=True) as mock_send:
        await manager.dispatch(NotificationEvent.NEW_ARTICLE, payload, db_session)

    mock_send.assert_called_once()


async def test_plugin_manager_skips_inactive(db_session):
    cfg = _make_plugin_config(is_active=False)
    db_session.add(cfg)
    await db_session.commit()

    payload = _make_payload()
    manager = PluginManager()

    with patch("app.plugins.telegram.TelegramPlugin.send", new_callable=AsyncMock, return_value=True) as mock_send:
        await manager.dispatch(NotificationEvent.NEW_ARTICLE, payload, db_session)

    mock_send.assert_not_called()


async def test_plugin_manager_continues_on_error(db_session):
    cfg = _make_plugin_config()
    db_session.add(cfg)
    await db_session.commit()

    payload = _make_payload()
    manager = PluginManager()

    with patch("app.plugins.telegram.TelegramPlugin.send", new_callable=AsyncMock, side_effect=RuntimeError("boom")):
        # Should not raise
        await manager.dispatch(NotificationEvent.NEW_ARTICLE, payload, db_session)


async def test_global_config_dispatched_to_all_users(db_session):
    """Config with user_id=None dispatches for any user."""
    cfg = _make_plugin_config(user_id=None)
    db_session.add(cfg)
    await db_session.commit()

    payload = _make_payload(user_id="some-other-user")
    manager = PluginManager()

    with patch("app.plugins.telegram.TelegramPlugin.send", new_callable=AsyncMock, return_value=True) as mock_send:
        await manager.dispatch(NotificationEvent.NEW_ARTICLE, payload, db_session)

    mock_send.assert_called_once()


async def test_user_specific_config_not_dispatched_for_other_user(db_session, regular_user):
    cfg = _make_plugin_config(user_id=regular_user.id)
    db_session.add(cfg)
    await db_session.commit()

    payload = _make_payload(user_id=str(uuid.uuid4()))  # different user
    manager = PluginManager()

    with patch("app.plugins.telegram.TelegramPlugin.send", new_callable=AsyncMock, return_value=True) as mock_send:
        await manager.dispatch(NotificationEvent.NEW_ARTICLE, payload, db_session)

    mock_send.assert_not_called()


async def test_unknown_plugin_type_skipped(db_session):
    cfg = PluginConfig(plugin_type="matrix", is_active=True, config_json_encrypted="x")
    cfg.id = uuid.uuid4()
    db_session.add(cfg)
    await db_session.commit()

    payload = _make_payload()
    manager = PluginManager()
    # Should not raise, just log warning
    await manager.dispatch(NotificationEvent.NEW_ARTICLE, payload, db_session)


# ---------------------------------------------------------------------------
# Admin API tests
# ---------------------------------------------------------------------------

async def test_admin_create_plugin(admin_client):
    resp = await admin_client.post("/api/v1/admin/plugins", json={
        "plugin_type": "telegram",
        "label": "My Telegram",
        "config_json": {"bot_token": "abc123", "chat_id": "456"},
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["plugin_type"] == "telegram"
    assert data["has_config"] is True
    assert "config_json" not in data  # never exposed


async def test_admin_list_plugins(admin_client, db_session):
    cfg = _make_plugin_config()
    db_session.add(cfg)
    await db_session.commit()

    resp = await admin_client.get("/api/v1/admin/plugins")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert all("config_json" not in d for d in data)


async def test_admin_create_unknown_plugin_type(admin_client):
    resp = await admin_client.post("/api/v1/admin/plugins", json={
        "plugin_type": "matrix",
        "config_json": {"something": "value"},
    })
    assert resp.status_code == 422


async def test_admin_create_missing_bot_token(admin_client):
    resp = await admin_client.post("/api/v1/admin/plugins", json={
        "plugin_type": "telegram",
        "config_json": {"chat_id": "123"},  # missing bot_token
    })
    assert resp.status_code == 422


async def test_admin_delete_plugin(admin_client, db_session):
    cfg = _make_plugin_config()
    db_session.add(cfg)
    await db_session.commit()

    resp = await admin_client.delete(f"/api/v1/admin/plugins/{cfg.id}")
    assert resp.status_code == 204


async def test_admin_list_available_plugins(admin_client):
    resp = await admin_client.get("/api/v1/admin/plugins/available")
    assert resp.status_code == 200
    data = resp.json()
    assert any(p["plugin_type"] == "telegram" for p in data)
    tg = next(p for p in data if p["plugin_type"] == "telegram")
    assert "config_schema" in tg
    assert "bot_token" in tg["config_schema"]
