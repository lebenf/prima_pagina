# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for Telegram plugin — mock httpx to avoid real HTTP calls."""
import uuid

import pytest
import respx
import httpx

from app.models.plugin_config import PluginConfig
from app.plugins.base import NotificationEvent, NotificationPayload
from app.plugins.telegram import TelegramPlugin


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(extra: dict | None = None) -> PluginConfig:
    cfg = PluginConfig(
        plugin_type="telegram",
        is_active=True,
        config_json_encrypted="",
    )
    cfg.id = uuid.uuid4()
    base = {
        "bot_token": "test-token",
        "chat_id": "123456",
        "notify_events": ["new_article", "digest_ready"],
        "digest_format": "summary",
    }
    if extra:
        base.update(extra)
    cfg.set_config(base)
    return cfg


def _plugin(extra: dict | None = None) -> TelegramPlugin:
    return TelegramPlugin(_make_config(extra))


def _article_payload() -> NotificationPayload:
    return NotificationPayload(
        event=NotificationEvent.NEW_ARTICLE,
        user_id="user-1",
        title="Breaking News",
        body="Something important happened today in the world.",
        url="https://example.com/news/1",
    )


def _digest_payload(html: str = "<h2>Politics</h2><p>Summary</p>") -> NotificationPayload:
    return NotificationPayload(
        event=NotificationEvent.DIGEST_READY,
        user_id="user-1",
        title="Rassegna Stampa — 22 aprile 2026",
        body="Politics: Summary. Economy: Another summary.",
        body_html=html,
        url="https://example.com/digests/d1",
    )


TELEGRAM_BASE = "https://api.telegram.org/bottest-token"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@respx.mock
async def test_send_new_article():
    respx.post(f"{TELEGRAM_BASE}/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    plugin = _plugin()
    result = await plugin.send(_article_payload())
    assert result is True
    assert respx.calls.call_count == 1
    sent = respx.calls[0].request
    import json
    body = json.loads(sent.content)
    assert "Breaking News" in body["text"]
    assert "📰" in body["text"]


@respx.mock
async def test_send_digest_summary():
    respx.post(f"{TELEGRAM_BASE}/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    plugin = _plugin({"digest_format": "summary"})
    result = await plugin.send(_digest_payload())
    assert result is True
    import json
    body = json.loads(respx.calls[0].request.content)
    assert "📋" in body["text"]
    assert "Rassegna Stampa" in body["text"]


@respx.mock
async def test_send_digest_full():
    respx.post(f"{TELEGRAM_BASE}/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    plugin = _plugin({"digest_format": "full"})
    result = await plugin.send(_digest_payload())
    assert result is True
    import json
    body = json.loads(respx.calls[0].request.content)
    # Full format should convert HTML
    assert "Politics" in body["text"]


@respx.mock
async def test_send_skips_disabled_event():
    """If event not in notify_events, returns True without calling API."""
    plugin = _plugin({"notify_events": ["digest_ready"]})  # no new_article
    result = await plugin.send(_article_payload())
    assert result is True
    assert respx.calls.call_count == 0


@respx.mock
async def test_test_connection_ok():
    respx.get(f"{TELEGRAM_BASE}/getMe").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {"username": "PrimaPaginaBot"}})
    )
    respx.post(f"{TELEGRAM_BASE}/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    plugin = _plugin()
    ok, msg = await plugin.test_connection()
    assert ok is True
    assert "PrimaPaginaBot" in msg


@respx.mock
async def test_test_connection_bad_token():
    respx.get(f"{TELEGRAM_BASE}/getMe").mock(
        return_value=httpx.Response(401, json={"ok": False, "description": "Unauthorized"})
    )
    plugin = _plugin()
    ok, msg = await plugin.test_connection()
    assert ok is False
    assert "Unauthorized" in msg or "Token" in msg


def test_html_escape():
    plugin = _plugin()
    assert plugin._escape_html("<script>alert('xss')</script>") == "&lt;script&gt;alert('xss')&lt;/script&gt;"
    assert plugin._escape_html("a & b") == "a &amp; b"


async def test_message_truncated_at_4096():
    plugin = _plugin({"digest_format": "full"})
    long_html = "<p>" + "A" * 5000 + "</p>"
    payload = _digest_payload(html=long_html)
    msg = plugin._format_message(payload)
    assert len(msg["text"]) <= 4096 + 50  # some slack for truncation marker


@respx.mock
async def test_send_returns_false_on_api_error():
    respx.post(f"{TELEGRAM_BASE}/sendMessage").mock(
        return_value=httpx.Response(400, json={"ok": False, "description": "Bad Request"})
    )
    plugin = _plugin()
    result = await plugin.send(_article_payload())
    assert result is False


@respx.mock
async def test_send_returns_false_on_network_error():
    respx.post(f"{TELEGRAM_BASE}/sendMessage").mock(side_effect=httpx.ConnectError("connection refused"))
    plugin = _plugin()
    result = await plugin.send(_article_payload())
    assert result is False


def test_convert_html_for_telegram():
    plugin = _plugin()
    html = "<h2>Politics</h2><p>Some <strong>important</strong> news.</p><article>wrap</article>"
    result = plugin._convert_html_for_telegram(html)
    assert "<b>Politics</b>" in result
    assert "<h2>" not in result
    assert "<article>" not in result
    assert "Some" in result


async def test_send_new_article_includes_inline_keyboard():
    """New article with URL should have an inline keyboard button."""
    import json as json_lib
    with respx.mock:
        respx.post(f"{TELEGRAM_BASE}/sendMessage").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        plugin = _plugin()
        await plugin.send(_article_payload())
        body = json_lib.loads(respx.calls[0].request.content)
        # reply_markup should have inline_keyboard with URL button
        rm = body.get("reply_markup")
        assert rm is not None
        assert rm["inline_keyboard"][0][0]["url"] == "https://example.com/news/1"


@respx.mock
async def test_send_no_url_no_keyboard():
    """No URL → no reply_markup sent."""
    import json as json_lib
    respx.post(f"{TELEGRAM_BASE}/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    plugin = _plugin()
    payload = NotificationPayload(
        event=NotificationEvent.NEW_ARTICLE,
        user_id="user-1",
        title="No Link Article",
        body="No URL here.",
        url=None,
    )
    await plugin.send(payload)
    body = json_lib.loads(respx.calls[0].request.content)
    assert body.get("reply_markup") is None
