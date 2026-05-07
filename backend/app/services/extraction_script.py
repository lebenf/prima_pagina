# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime

from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------


@dataclass
class SelectorValidation:
    content_found: bool
    content_length: int
    title_found: bool
    author_found: bool
    date_found: bool


def validate_selectors(selectors: dict, html: str) -> SelectorValidation:
    """Apply selectors to HTML and check that content is found."""
    soup = BeautifulSoup(html, "lxml")

    content_text = ""
    if selectors.get("content"):
        el = soup.select_one(selectors["content"])
        content_text = el.get_text(strip=True) if el else ""

    return SelectorValidation(
        content_found=len(content_text) > 100,
        content_length=len(content_text),
        title_found=bool(selectors.get("title") and soup.select_one(selectors["title"])),
        author_found=bool(selectors.get("author") and soup.select_one(selectors["author"])),
        date_found=bool(selectors.get("date") and soup.select_one(selectors["date"])),
    )


# ---------------------------------------------------------------------------
# HTML utilities
# ---------------------------------------------------------------------------


def _hash_body(html: str) -> str:
    """SHA256 of body structure (tag+classes only, not text) — stable across content changes."""
    soup = BeautifulSoup(html, "lxml")
    body = soup.find("body")
    if not body:
        return hashlib.sha256(html[:1000].encode()).hexdigest()
    structure = "".join(
        f"{tag.name}.{' '.join(tag.get('class', []))}"
        for tag in body.find_all(True)
    )
    return hashlib.sha256(structure.encode()).hexdigest()


def _truncate_html_for_prompt(html: str, max_chars: int = 40_000) -> str:
    """Intelligent truncation: parse then slice to avoid mid-tag cuts."""
    if len(html) <= max_chars:
        return html
    soup = BeautifulSoup(html[: max_chars * 2], "lxml")
    return str(soup)[:max_chars]


# ---------------------------------------------------------------------------
# Script application
# ---------------------------------------------------------------------------


def apply_extraction_script(
    script,
    html: str,
    fallback_title: str | None = None,
    fallback_author: str | None = None,
) -> dict:
    """Apply CSS selectors to HTML. All fields can be None."""
    soup = BeautifulSoup(html, "lxml")
    result: dict = {}

    if script.selectors.get("content"):
        el = soup.select_one(script.selectors["content"])
        if el:
            for unwanted in el.select("script, style, nav, .advertisement, .ad, .share"):
                unwanted.decompose()
            result["content"] = el.get_text(separator="\n", strip=True)

    if script.selectors.get("title"):
        el = soup.select_one(script.selectors["title"])
        result["title"] = el.get_text(strip=True) if el else fallback_title
    else:
        result["title"] = fallback_title

    if script.selectors.get("author"):
        el = soup.select_one(script.selectors["author"])
        result["author"] = el.get_text(strip=True) if el else fallback_author
    else:
        result["author"] = fallback_author

    if script.selectors.get("date"):
        el = soup.select_one(script.selectors["date"])
        if el:
            result["date"] = el.get("datetime") or el.get_text(strip=True)

    return result


# ---------------------------------------------------------------------------
# LLM prompt and parsing
# ---------------------------------------------------------------------------


def _build_selector_prompt(html: str, url: str, site_url: str | None, feedback: str | None = None) -> str:
    feedback_section = (
        f"\nFeedback utente sul precedente tentativo di estrazione:\n{feedback}\nTieni conto di questo problema nella scelta dei selector.\n"
        if feedback else ""
    )
    return f"""Analizza questo HTML e trova i CSS selector per estrarre il contenuto dell'articolo.

URL della pagina: {url}
Sito: {site_url or 'sconosciuto'}
{feedback_section}
HTML (troncato):
{html}

Rispondi SOLO con un oggetto JSON valido, nessun altro testo:
{{
  "content": "selector CSS per il corpo dell'articolo (obbligatorio)",
  "title": "selector CSS per il titolo (opzionale, null se non trovato)",
  "author": "selector CSS per l'autore (opzionale, null se non trovato)",
  "date": "selector CSS per la data (opzionale, null se non trovato)",
  "reasoning": "breve spiegazione della scelta (max 100 chars)"
}}

Regole:
- Scegli selector che selezionano il testo principale dell'articolo, non la navigazione o i commenti
- Preferisci selector semantici (article, main, .post-content) a quelli strutturali (div > div)
- Il selector 'content' deve selezionare un elemento che contiene il testo completo
- Se non sei sicuro del selector per title/author/date, metti null
"""


def _parse_selector_response(raw: str) -> dict:
    """Parse LLM JSON response, handle markdown code fences."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        cleaned = parts[1] if len(parts) > 1 else cleaned
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()
    try:
        data = json.loads(cleaned)
        return {
            k: v
            for k, v in {
                "content": data.get("content"),
                "title": data.get("title"),
                "author": data.get("author"),
                "date": data.get("date"),
            }.items()
            if v
        }
    except (json.JSONDecodeError, AttributeError):
        return {}


# ---------------------------------------------------------------------------
# Main generation function
# ---------------------------------------------------------------------------


async def generate_extraction_script(
    feed,
    sample_url: str,
    html_content: str,
    db: AsyncSession,
    feedback: str | None = None,
):
    """
    Ask LLM for CSS selectors, validate, save.
    Returns saved FeedExtractionScript or None on failure.
    """
    from app.models.feed_extraction_script import FeedExtractionScript
    from app.services.llm.router import llm_router

    provider = await llm_router.get_provider_for("tagging", db)
    if not provider:
        logger.warning("no LLM provider for extraction script generation (feed %s)", feed.id)
        return None

    truncated_html = _truncate_html_for_prompt(html_content, max_chars=40_000)
    prompt = _build_selector_prompt(truncated_html, sample_url, feed.site_url, feedback)

    try:
        raw_response = await provider.generate_text(prompt, max_tokens=500)
        selectors = _parse_selector_response(raw_response)
    except Exception as exc:
        logger.error("LLM selector generation failed for feed %s: %s", feed.id, exc)
        return None

    if not selectors.get("content"):
        logger.warning("LLM did not provide content selector for feed %s", feed.id)
        return None

    validation = validate_selectors(selectors, html_content)
    if not validation.content_found:
        logger.warning(
            "content selector '%s' found no content on %s — not saving",
            selectors["content"],
            sample_url,
        )
        return None

    body_hash = _hash_body(html_content)
    now = datetime.utcnow()

    # Invalidate any existing script first
    existing = await db.get(FeedExtractionScript, feed.id)
    if existing:
        existing.is_active = False

    script = FeedExtractionScript(
        feed_id=feed.id,
        selectors=selectors,
        generated_at=now,
        validated_at=now,
        is_active=True,
        success_rate=1.0,
        consecutive_failures=0,
        sample_url=sample_url,
        sample_html_hash=body_hash,
    )
    db.add(script)
    await db.commit()
    logger.info("extraction script saved for feed %s: %s", feed.id, selectors)
    return script
