# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import re

import anthropic

from app.services.llm.base import DigestResult, LLMProvider, TaggingResult

logger = logging.getLogger(__name__)


class ClaudeProvider(LLMProvider):
    """Anthropic Claude API provider. Preferred for digest generation."""

    def __init__(self, config, encryption_key: str = ""):
        super().__init__(config)
        api_key = self._resolve_api_key(config, encryption_key)
        timeout_sec = getattr(config, "timeout_sec", 300)
        self._client = anthropic.AsyncAnthropic(api_key=api_key, timeout=float(timeout_sec))

    @staticmethod
    def _resolve_api_key(config, encryption_key: str) -> str:
        if config.api_key_encrypted and encryption_key:
            try:
                return config.get_api_key(encryption_key) or ""
            except Exception:
                pass
        from app.config import get_settings
        return get_settings().anthropic_api_key

    async def tag_article(
        self,
        title: str,
        excerpt: str,
        language: str | None,
        available_categories: list[str],
    ) -> TaggingResult:
        prompt = self._build_tagging_prompt(title, excerpt, language, available_categories)
        try:
            message = await self._client.messages.create(
                model=self.model,
                max_tokens=300,
                system="You classify news articles. Reply ONLY with valid JSON, no markdown.",
                messages=[{"role": "user", "content": prompt}],
            )
            return self._parse_tagging_json(message.content[0].text)
        except anthropic.APIError as exc:
            logger.error("claude: tagging API error: %s", exc)
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
        articles_text = self._format_articles_for_prompt(articles)

        system_prompt = (
            f"You are an expert journalist writing professional press digests. "
            f"Always write in {lang_name}. Cite sources. Be factual and concise.\n{style_hints}"
        )
        user_prompt = (
            f"Write a press digest for {period_label}.\n\n"
            f"Articles:\n{articles_text}\n\n"
            "Output HTML with <h2> per thematic section, <article> per story "
            "(<h3> title, <p> summary ≤150 words, <cite> source+link). "
            "Add a 2-3 sentence introduction."
        )
        try:
            message = await self._client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            content_html = message.content[0].text
            content_text = self._html_to_text(content_html)
            title = self._extract_title(content_html, period_label)
            return DigestResult(
                title=title,
                content_html=content_html,
                content_text=content_text,
                article_count=len(articles),
            )
        except anthropic.APIError as exc:
            logger.error("claude: digest API error: %s", exc)
            raise

    async def generate_text(self, prompt: str, max_tokens: int = 500) -> str:
        try:
            message = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except Exception as exc:
            logger.error("claude: generate_text error: %s", exc)
            return ""

    async def health_check(self) -> bool:
        try:
            await self._client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False

    def _format_articles_for_prompt(self, articles: list[dict]) -> str:
        parts = []
        total = 0
        max_chars = 60_000
        for i, art in enumerate(articles, 1):
            content = (art.get("fulltext") or art.get("excerpt", ""))[:1500]
            part = f"[{i}] {art.get('source', '')} — {art.get('title', '')}\n{content}\nURL: {art.get('url', '')}\n"
            if total + len(part) > max_chars:
                break
            parts.append(part)
            total += len(part)
        return "\n---\n".join(parts)

    @staticmethod
    def _html_to_text(html: str) -> str:
        text = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _extract_title(html: str, fallback: str) -> str:
        m = re.search(r"<h[12][^>]*>(.*?)</h[12]>", html, re.IGNORECASE | re.DOTALL)
        if m:
            return re.sub(r"<[^>]+>", "", m.group(1)).strip()
        return f"Rassegna stampa — {fallback}"
