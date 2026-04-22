import logging
import re

import httpx

from app.plugins.base import NotificationEvent, NotificationPayload, NotificationPlugin

logger = logging.getLogger(__name__)


class TelegramPlugin(NotificationPlugin):
    """
    Plugin Telegram: invia notifiche tramite Bot API.

    Configurazione:
    - bot_token: token del bot (da @BotFather)
    - chat_id: ID chat/gruppo/canale
    - notify_events: lista eventi (default: ["new_article", "digest_ready"])
    - digest_format: "full" | "summary"
    - article_filter: {tags, category_slug} (opzionale)
    """

    plugin_type = "telegram"
    config_schema = {
        "bot_token": {"type": "string", "required": True, "secret": True, "label": "Bot Token"},
        "chat_id": {"type": "string", "required": True, "secret": False, "label": "Chat ID"},
        "notify_events": {"type": "list", "required": False, "default": ["new_article", "digest_ready"]},
        "digest_format": {"type": "string", "required": False, "default": "summary"},
        "article_filter": {"type": "object", "required": False, "default": {}},
    }

    _BASE_URL = "https://api.telegram.org/bot{token}"

    async def send(self, payload: NotificationPayload) -> bool:
        token = self._cfg.get("bot_token", "")
        chat_id = self._cfg.get("chat_id", "")
        notify_events = self._cfg.get("notify_events", ["new_article", "digest_ready"])

        if payload.event.value not in notify_events:
            return True

        try:
            message = self._format_message(payload)
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    self._BASE_URL.format(token=token) + "/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": message["text"],
                        "parse_mode": message.get("parse_mode", "HTML"),
                        "disable_web_page_preview": False,
                        "reply_markup": message.get("reply_markup"),
                    },
                )
            if res.status_code == 200:
                return True
            logger.warning("telegram: sendMessage failed: %s %s", res.status_code, res.text[:200])
            return False
        except Exception as e:
            logger.error("telegram: send error: %s", e)
            return False

    def _format_message(self, payload: NotificationPayload) -> dict:
        if payload.event == NotificationEvent.NEW_ARTICLE:
            text = f"📰 <b>{self._escape_html(payload.title)}</b>\n\n"
            if payload.body:
                excerpt = payload.body[:200] + ("..." if len(payload.body) > 200 else "")
                text += f"{self._escape_html(excerpt)}\n\n"
            reply_markup = None
            if payload.url:
                reply_markup = {"inline_keyboard": [[{"text": "Leggi articolo →", "url": payload.url}]]}
            return {"text": text, "reply_markup": reply_markup}

        elif payload.event == NotificationEvent.DIGEST_READY:
            digest_format = self._cfg.get("digest_format", "summary")
            text = f"📋 <b>{self._escape_html(payload.title)}</b>\n\n"

            if digest_format == "full" and payload.body_html:
                telegram_html = self._convert_html_for_telegram(payload.body_html)
                if len(telegram_html) > 4000:
                    telegram_html = telegram_html[:4000] + "\n\n<i>... [troncato]</i>"
                text += telegram_html
            else:
                text += self._escape_html(payload.body[:500] if payload.body else "")

            reply_markup = None
            if payload.url:
                reply_markup = {"inline_keyboard": [[{"text": "Leggi rassegna completa →", "url": payload.url}]]}
            return {"text": text, "reply_markup": reply_markup}

        else:
            text = f"ℹ️ <b>{self._escape_html(payload.title)}</b>\n{self._escape_html(payload.body)}"
            return {"text": text}

    def _convert_html_for_telegram(self, html: str) -> str:
        result = html
        result = re.sub(r'<h[23][^>]*>(.*?)</h[23]>', r'<b>\1</b>\n', result, flags=re.DOTALL)
        result = re.sub(r'</?article[^>]*>', '', result)
        result = re.sub(r'<cite[^>]*>(.*?)</cite>', r'<i>\1</i>', result, flags=re.DOTALL)
        result = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', result, flags=re.DOTALL)
        result = re.sub(r'<(?!/?(?:b|i|u|s|a|code|pre)(?:\s[^>]*)?>)[^>]+>', '', result)
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result.strip()

    @staticmethod
    def _escape_html(text: str) -> str:
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    async def test_connection(self) -> tuple[bool, str]:
        token = self._cfg.get("bot_token", "")
        chat_id = self._cfg.get("chat_id", "")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(self._BASE_URL.format(token=token) + "/getMe")
                if res.status_code != 200:
                    return False, f"Token non valido: {res.json().get('description', 'errore')}"

                bot_name = res.json()["result"]["username"]

                test_res = await client.post(
                    self._BASE_URL.format(token=token) + "/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": f"✅ Prima Pagina — connessione verificata (@{bot_name})",
                        "parse_mode": "HTML",
                    },
                )
                if test_res.status_code == 200:
                    return True, f"Connessione OK. Bot: @{bot_name}"
                return False, f"Chat ID non valido: {test_res.json().get('description', 'errore')}"

        except Exception as e:
            return False, f"Errore di connessione: {e}"
