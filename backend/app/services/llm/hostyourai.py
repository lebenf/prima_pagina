# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import re

import httpx

from app.services.llm.base import DigestResult, LLMProvider, TaggingResult

logger = logging.getLogger(__name__)


class HostYourAIProvider(LLMProvider):
    """HostYourAI OpenAI-compatible API provider, called via raw HTTP (no SDK dependency)."""

    DEFAULT_ENDPOINT = "https://hostyourai.com/api/v1"

    def __init__(self, config, encryption_key: str = ""):
        super().__init__(config)
        self.base_url = (config.endpoint_url or self.DEFAULT_ENDPOINT).rstrip("/")
        self.timeout_sec = getattr(config, "timeout_sec", None) or 300
        self.api_key = self._resolve_api_key(config, encryption_key)

    @staticmethod
    def _resolve_api_key(config, encryption_key: str) -> str:
        if config.api_key_encrypted and encryption_key:
            try:
                return config.get_api_key(encryption_key) or ""
            except Exception:
                pass
        from app.config import get_settings
        return get_settings().hostyourai_api_key

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def _chat_complete(self, prompt: str, max_tokens: int, json_mode: bool = False) -> str:
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        async with httpx.AsyncClient(timeout=float(self.timeout_sec)) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=body,
            )
            response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]
        message = choice.get("message") or {}
        # Reasoning models (e.g. Qwen3.5) may burn the whole max_tokens budget on
        # hidden chain-of-thought and return content: null with the CoT text left
        # in reasoning_content instead.
        content = message.get("content") or message.get("reasoning_content")
        if not content:
            finish_reason = choice.get("finish_reason")
            logger.error(
                "hostyourai: empty content for model %s (finish_reason=%s)",
                self.model, finish_reason,
            )
            raise ValueError(
                f"hostyourai: risposta vuota dal modello (finish_reason={finish_reason}) "
                "— probabile budget di token insufficiente per un modello di reasoning"
            )
        return content

    async def tag_article(
        self,
        title: str,
        excerpt: str,
        language: str | None,
        available_categories: list[str],
        tagging_language: str = "it",
        existing_tags: list[str] | None = None,
    ) -> TaggingResult:
        prompt = self._build_tagging_prompt(
            title, excerpt, language, available_categories,
            tagging_language=tagging_language, existing_tags=existing_tags,
        )
        try:
            raw = await self._chat_complete(prompt, max_tokens=800, json_mode=True)
            return self._parse_tagging_json(raw)
        except httpx.TimeoutException:
            logger.warning("hostyourai: tag_article timeout for model %s", self.model)
            return TaggingResult()
        except Exception as exc:
            logger.error("hostyourai: tag_article error: %s", exc)
            return TaggingResult()

    async def generate_digest(
        self,
        articles: list[dict],
        period_label: str,
        output_language: str,
        style_hints: str = "",
    ) -> DigestResult:
        lang_names = {
            "it": "italiano", "en": "English", "fr": "français",
            "de": "Deutsch", "es": "español", "pt": "português",
        }
        lang_name = lang_names.get(output_language, output_language)
        articles_text = self._format_articles(articles)

        prompt = (
            f"Write a professional press digest in {lang_name} for {period_label}.\n\n"
            f"Articles:\n{articles_text}\n\n"
            f"{style_hints}\n\n"
            "Format: HTML with <h2> for sections, <article> per story. "
            "When a URL is given above for a story, cite the source as "
            '<cite><a href="EXACT_URL_FROM_ABOVE">Source name</a></cite> — use the URL '
            "exactly as given, never invent or alter it. If no URL is given, cite only "
            "the source name in plain text. When a story lists multiple 'Fonti' (sources) "
            "instead of a single source, it means several outlets covered the same story: "
            "write exactly ONE <article> for it, citing every listed source with its own "
            "<cite><a> — never write a separate <article> per source for the same story. "
            "Reply with the HTML only — no introduction, no explanation, no markdown "
            "code fences, start directly with the markup."
        )
        try:
            raw = await self._chat_complete(prompt, max_tokens=8000)
            content_html = self._clean_html_response(raw)
            content_text = re.sub(r"<[^>]+>", " ", content_html).strip()
            title = f"Rassegna stampa — {period_label}"
            return DigestResult(
                title=title,
                content_html=content_html,
                content_text=content_text,
                article_count=len(articles),
            )
        except Exception as exc:
            logger.error("hostyourai: generate_digest error: %s", exc)
            raise

    async def generate_text(self, prompt: str, max_tokens: int = 500, json_mode: bool = False) -> str:
        try:
            return await self._chat_complete(prompt, max_tokens=max_tokens, json_mode=json_mode)
        except Exception as exc:
            logger.error("hostyourai: generate_text error: %s", exc)
            return ""

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/models", headers=self._headers())
                return res.status_code == 200
        except Exception:
            return False

    @staticmethod
    def _format_articles(articles: list[dict]) -> str:
        parts = []
        total = 0
        for i, art in enumerate(articles, 1):
            content = (art.get("fulltext") or art.get("excerpt", ""))[:1000]
            sources = art.get("sources")
            if sources:
                sources_text = "\n".join(f"  - {s['source']}: {s['url']}" for s in sources)
                header = f"[{i}] {art.get('title', '')}\nFonti:\n{sources_text}\n"
            else:
                header = (
                    f"[{i}] {art.get('source', '')} — {art.get('title', '')}\n"
                    f"URL: {art.get('url', '')}\n"
                )
            part = f"{header}{content}\n"
            if total + len(part) > 40_000:
                break
            parts.append(part)
            total += len(part)
        return "\n---\n".join(parts)
