import logging
import re

import httpx

from app.services.llm.base import DigestResult, LLMProvider, TaggingResult

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Self-hosted Ollama provider. Preferred for tagging: low latency, zero cost."""

    def __init__(self, config):
        super().__init__(config)
        self.base_url = (config.endpoint_url or "http://localhost:11434").rstrip("/")

    async def tag_article(
        self,
        title: str,
        excerpt: str,
        language: str | None,
        available_categories: list[str],
    ) -> TaggingResult:
        prompt = self._build_tagging_prompt(title, excerpt, language, available_categories)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0.1, "num_predict": 200},
                    },
                )
                response.raise_for_status()
            return self._parse_tagging_json(response.json()["response"])
        except httpx.TimeoutException:
            logger.warning("ollama: tag_article timeout for model %s", self.model)
            return TaggingResult()
        except Exception as exc:
            logger.error("ollama: tag_article error: %s", exc)
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
            "Format: HTML with <h2> for sections, <article> per story."
        )
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.5, "num_predict": 2000},
                    },
                )
                response.raise_for_status()
            content_html = response.json()["response"]
            content_text = re.sub(r"<[^>]+>", " ", content_html).strip()
            title = f"Rassegna stampa — {period_label}"
            return DigestResult(
                title=title,
                content_html=content_html,
                content_text=content_text,
                article_count=len(articles),
            )
        except Exception as exc:
            logger.error("ollama: generate_digest error: %s", exc)
            raise

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    @staticmethod
    def _format_articles(articles: list[dict]) -> str:
        parts = []
        total = 0
        for i, art in enumerate(articles, 1):
            content = (art.get("fulltext") or art.get("excerpt", ""))[:1000]
            part = f"[{i}] {art.get('source', '')} — {art.get('title', '')}\n{content}\n"
            if total + len(part) > 40_000:
                break
            parts.append(part)
            total += len(part)
        return "\n---\n".join(parts)
