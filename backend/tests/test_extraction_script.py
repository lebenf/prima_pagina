# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for app/services/extraction_script.py"""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.extraction_script import (
    SelectorValidation,
    _hash_body,
    _parse_selector_response,
    _truncate_html_for_prompt,
    apply_extraction_script,
    generate_extraction_script,
    validate_selectors,
)

# ---------------------------------------------------------------------------
# Sample HTML fixture
# ---------------------------------------------------------------------------

SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head><title>Test Article</title></head>
<body>
  <header><nav>Navigation</nav></header>
  <main>
    <h1 class="entry-title">My Article Title</h1>
    <span class="author-name">John Doe</span>
    <time class="published" datetime="2026-01-15">January 15, 2026</time>
    <article class="post-content">
      <p>This is the main content of the article. It is long enough to pass validation.
      Lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor
      incididunt ut labore et dolore magna aliqua.</p>
      <p>Another paragraph with more content to make it long enough.</p>
    </article>
  </main>
</body>
</html>"""

MODIFIED_HTML = """<!DOCTYPE html>
<html>
<head><title>Test Article</title></head>
<body>
  <div class="new-layout">
    <section class="content-wrapper">
      <h1>Different Layout Title</h1>
      <div class="body-text">Content here.</div>
    </section>
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# validate_selectors
# ---------------------------------------------------------------------------


def test_validate_selectors_found():
    selectors = {
        "content": "article.post-content",
        "title": "h1.entry-title",
        "author": ".author-name",
        "date": "time.published",
    }
    result = validate_selectors(selectors, SAMPLE_HTML)
    assert result.content_found is True
    assert result.content_length > 100
    assert result.title_found is True
    assert result.author_found is True
    assert result.date_found is True


def test_validate_selectors_not_found():
    selectors = {"content": ".nonexistent-class"}
    result = validate_selectors(selectors, SAMPLE_HTML)
    assert result.content_found is False
    assert result.content_length == 0
    assert result.title_found is False


def test_validate_selectors_no_content_key():
    result = validate_selectors({}, SAMPLE_HTML)
    assert result.content_found is False


# ---------------------------------------------------------------------------
# _hash_body
# ---------------------------------------------------------------------------


def test_hash_body_stable():
    h1 = _hash_body(SAMPLE_HTML)
    h2 = _hash_body(SAMPLE_HTML)
    assert h1 == h2


def test_hash_body_changes_on_layout_change():
    h_original = _hash_body(SAMPLE_HTML)
    h_modified = _hash_body(MODIFIED_HTML)
    assert h_original != h_modified


def test_hash_body_stable_across_text_changes():
    """Same structure with different text content → same hash."""
    html_v1 = SAMPLE_HTML.replace("My Article Title", "Different Title")
    html_v2 = SAMPLE_HTML.replace("John Doe", "Jane Smith")
    # Structure (tag+class) unchanged → hashes should match
    assert _hash_body(html_v1) == _hash_body(html_v2)


def test_hash_body_empty_html():
    h = _hash_body("<html></html>")
    assert isinstance(h, str) and len(h) == 64


# ---------------------------------------------------------------------------
# apply_extraction_script
# ---------------------------------------------------------------------------


def _make_script(selectors):
    s = MagicMock()
    s.selectors = selectors
    return s


def test_apply_script_extracts_content():
    script = _make_script({"content": "article.post-content"})
    result = apply_extraction_script(script, SAMPLE_HTML)
    assert "content" in result
    assert len(result["content"]) > 50


def test_apply_script_extracts_all_fields():
    script = _make_script({
        "content": "article.post-content",
        "title": "h1.entry-title",
        "author": ".author-name",
        "date": "time.published",
    })
    result = apply_extraction_script(script, SAMPLE_HTML)
    assert result["content"]
    assert result["title"] == "My Article Title"
    assert result["author"] == "John Doe"
    assert result["date"] == "2026-01-15"


def test_apply_script_fallback_title():
    script = _make_script({"content": "article.post-content"})
    result = apply_extraction_script(script, SAMPLE_HTML, fallback_title="RSS Title")
    assert result["title"] == "RSS Title"


def test_apply_script_fallback_author():
    script = _make_script({"content": "article.post-content", "author": ".missing"})
    result = apply_extraction_script(script, SAMPLE_HTML, fallback_author="RSS Author")
    assert result["author"] == "RSS Author"


def test_apply_script_no_content_match():
    script = _make_script({"content": ".missing-selector"})
    result = apply_extraction_script(script, SAMPLE_HTML)
    assert "content" not in result


# ---------------------------------------------------------------------------
# _truncate_html_for_prompt
# ---------------------------------------------------------------------------


def test_truncate_html_short():
    """HTML shorter than max_chars returned unchanged."""
    short = "<p>Hello</p>"
    assert _truncate_html_for_prompt(short, max_chars=100) == short


def test_truncate_html_long():
    very_long = SAMPLE_HTML * 50
    result = _truncate_html_for_prompt(very_long, max_chars=500)
    assert len(result) <= 500


# ---------------------------------------------------------------------------
# _parse_selector_response
# ---------------------------------------------------------------------------


def test_parse_selector_response_valid():
    raw = '{"content": "article.post", "title": "h1", "author": null, "date": null}'
    result = _parse_selector_response(raw)
    assert result["content"] == "article.post"
    assert result["title"] == "h1"
    assert "author" not in result
    assert "date" not in result


def test_parse_selector_response_with_markdown_fence():
    raw = '```json\n{"content": "main", "title": "h1"}\n```'
    result = _parse_selector_response(raw)
    assert result["content"] == "main"
    assert result["title"] == "h1"


def test_parse_selector_response_invalid_json():
    result = _parse_selector_response("not json at all")
    assert result == {}


def test_parse_selector_response_empty_string():
    result = _parse_selector_response("")
    assert result == {}


# ---------------------------------------------------------------------------
# generate_extraction_script (async, mocked LLM)
# ---------------------------------------------------------------------------


async def test_generate_script_success(db_session, sample_feed):
    from app.services.llm.router import llm_router

    mock_provider = AsyncMock()
    mock_provider.generate_text = AsyncMock(
        return_value='{"content": "article.post-content", "title": "h1.entry-title"}'
    )

    original_get = llm_router.get_provider_for
    llm_router.get_provider_for = AsyncMock(return_value=mock_provider)

    try:
        script = await generate_extraction_script(
            sample_feed, "https://example.com/article", SAMPLE_HTML, db_session
        )
        assert script is not None
        assert script.selectors["content"] == "article.post-content"
        assert script.is_active is True
        assert script.validated_at is not None
    finally:
        llm_router.get_provider_for = original_get


async def test_generate_script_no_content_selector(db_session, sample_feed):
    from app.services.llm.router import llm_router

    mock_provider = AsyncMock()
    mock_provider.generate_text = AsyncMock(
        return_value='{"title": "h1", "author": ".author"}'
    )
    llm_router.get_provider_for = AsyncMock(return_value=mock_provider)

    try:
        script = await generate_extraction_script(
            sample_feed, "https://example.com/article", SAMPLE_HTML, db_session
        )
        assert script is None
    finally:
        llm_router.get_provider_for = AsyncMock(return_value=None)


async def test_generate_script_validation_fails(db_session, sample_feed):
    from app.services.llm.router import llm_router

    mock_provider = AsyncMock()
    # Selector that won't match anything in SAMPLE_HTML
    mock_provider.generate_text = AsyncMock(
        return_value='{"content": ".nonexistent-class-xyz"}'
    )
    llm_router.get_provider_for = AsyncMock(return_value=mock_provider)

    try:
        script = await generate_extraction_script(
            sample_feed, "https://example.com/article", SAMPLE_HTML, db_session
        )
        assert script is None
    finally:
        llm_router.get_provider_for = AsyncMock(return_value=None)


async def test_generate_script_no_provider(db_session, sample_feed):
    from app.services.llm.router import llm_router

    original = llm_router.get_provider_for
    llm_router.get_provider_for = AsyncMock(return_value=None)
    try:
        script = await generate_extraction_script(
            sample_feed, "https://example.com/article", SAMPLE_HTML, db_session
        )
        assert script is None
    finally:
        llm_router.get_provider_for = original
