# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for app/services/full_text.py"""
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.models.article import Article, FulltextStatus
from app.models.feed import Feed


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_article(
    db_session,
    *,
    url="https://example.com/article",
    status=FulltextStatus.PENDING.value,
    fulltext_enabled=True,
):
    feed = Feed(
        url=f"https://example.com/{uuid4()}/feed.xml",
        title="Test Feed",
        fulltext_enabled=fulltext_enabled,
    )
    db_session.add(feed)
    await db_session.flush()
    article = Article(
        feed_id=feed.id,
        guid=str(uuid4()),
        title="Test Article",
        url=url,
        fulltext_status=status,
        tags=[],
        tags_source="none",
    )
    db_session.add(article)
    await db_session.commit()
    await db_session.refresh(article)
    return article


# ---------------------------------------------------------------------------
# Basic fetch behaviour
# ---------------------------------------------------------------------------


async def test_fetch_fulltext_success(db_session):
    """A successful extraction sets fulltext_status=OK and stores the content."""
    article = await _make_article(db_session)
    long_content = "This is the full article text. " * 20  # > 200 chars

    with patch("app.services.full_text._extract_fulltext_sync", return_value=long_content):
        from app.services.full_text import process_fulltext
        await process_fulltext(article.id, db_session)

    await db_session.refresh(article)
    assert article.fulltext_status == FulltextStatus.OK.value
    assert article.content_fulltext == long_content
    assert article.fulltext_fetched_at is not None


async def test_fetch_fulltext_failed_short_content(db_session):
    """Content shorter than 200 chars sets fulltext_status=FAILED."""
    article = await _make_article(db_session)

    with patch("app.services.full_text._extract_fulltext_sync", return_value="Too short."):
        from app.services.full_text import process_fulltext
        await process_fulltext(article.id, db_session)

    await db_session.refresh(article)
    assert article.fulltext_status == FulltextStatus.FAILED.value
    assert article.content_fulltext is None


async def test_fetch_fulltext_no_double_fetch(db_session):
    """If fulltext_status is already OK, a second call is a no-op."""
    article = await _make_article(db_session, status=FulltextStatus.OK.value)
    article.content_fulltext = "Already fetched content"
    await db_session.commit()

    with patch("app.services.full_text._extract_fulltext_sync") as mock_extract:
        from app.services.full_text import process_fulltext
        await process_fulltext(article.id, db_session)
        mock_extract.assert_not_called()

    await db_session.refresh(article)
    assert article.fulltext_status == FulltextStatus.OK.value


async def test_fetch_fulltext_exception_sets_failed(db_session):
    """An exception during extraction sets fulltext_status=FAILED."""
    article = await _make_article(db_session)

    with patch(
        "app.services.full_text._extract_fulltext_sync",
        side_effect=ConnectionError("Network error"),
    ):
        from app.services.full_text import process_fulltext
        await process_fulltext(article.id, db_session)

    await db_session.refresh(article)
    assert article.fulltext_status == FulltextStatus.FAILED.value
    assert article.content_fulltext is None


async def test_fetch_fulltext_no_url_sets_failed(db_session):
    """An article without a URL is immediately marked as FAILED."""
    article = await _make_article(db_session, url=None)

    with patch("app.services.full_text._extract_fulltext_sync") as mock_extract:
        from app.services.full_text import process_fulltext
        await process_fulltext(article.id, db_session)
        mock_extract.assert_not_called()

    await db_session.refresh(article)
    assert article.fulltext_status == FulltextStatus.FAILED.value


async def test_fetch_fulltext_deduplication(db_session):
    """is_fetch_active returns True while a fetch is in progress."""
    from app.services.full_text import _active_fetches, is_fetch_active

    article = await _make_article(db_session)
    assert not is_fetch_active(article.id)

    # Manually add to active set to simulate in-progress
    _active_fetches.add(article.id)
    assert is_fetch_active(article.id)

    _active_fetches.discard(article.id)
    assert not is_fetch_active(article.id)


# ---------------------------------------------------------------------------
# fulltext_enabled gate
# ---------------------------------------------------------------------------


async def test_fulltext_disabled_sets_blocked(db_session):
    """Feed with fulltext_enabled=False → article gets BLOCKED, extractor not called."""
    article = await _make_article(db_session, fulltext_enabled=False)

    with patch("app.services.full_text._extract_fulltext_sync") as mock_extract:
        from app.services.full_text import process_fulltext
        await process_fulltext(article.id, db_session)
        mock_extract.assert_not_called()

    await db_session.refresh(article)
    assert article.fulltext_status == FulltextStatus.BLOCKED.value
    assert article.content_fulltext is None


async def test_fulltext_enabled_proceeds(db_session):
    """Feed with fulltext_enabled=True → extraction runs."""
    article = await _make_article(db_session, fulltext_enabled=True)
    long_content = "X" * 300

    with patch("app.services.full_text._extract_fulltext_sync", return_value=long_content):
        from app.services.full_text import process_fulltext
        await process_fulltext(article.id, db_session)

    await db_session.refresh(article)
    assert article.fulltext_status == FulltextStatus.OK.value


# ---------------------------------------------------------------------------
# include_images passthrough
# ---------------------------------------------------------------------------


async def test_include_images_false_passed_to_extractor(db_session):
    """fulltext_include_images=False → _extract_fulltext_sync called with include_images=False."""
    feed = Feed(
        url=f"https://noimages.example.com/{uuid4()}/feed.xml",
        title="No Images Feed",
        fulltext_enabled=True,
        fulltext_mode="trafilatura",
        fulltext_include_images=False,
    )
    db_session.add(feed)
    await db_session.flush()
    article = Article(
        feed_id=feed.id,
        guid=str(uuid4()),
        url="https://example.com/article",
        fulltext_status=FulltextStatus.PENDING.value,
        tags=[],
        tags_source="none",
    )
    db_session.add(article)
    await db_session.commit()

    with patch("app.services.full_text._extract_fulltext_sync", return_value="Z" * 300) as mock_ext:
        from app.services.full_text import process_fulltext
        await process_fulltext(article.id, db_session)

    mock_ext.assert_called_once_with(article.url, False)


async def test_include_images_true_passed_to_extractor(db_session):
    """fulltext_include_images=True → _extract_fulltext_sync called with include_images=True."""
    feed = Feed(
        url=f"https://withimages.example.com/{uuid4()}/feed.xml",
        title="Images Feed",
        fulltext_enabled=True,
        fulltext_mode="trafilatura",
        fulltext_include_images=True,
    )
    db_session.add(feed)
    await db_session.flush()
    article = Article(
        feed_id=feed.id,
        guid=str(uuid4()),
        url="https://example.com/comic",
        fulltext_status=FulltextStatus.PENDING.value,
        tags=[],
        tags_source="none",
    )
    db_session.add(article)
    await db_session.commit()

    with patch("app.services.full_text._extract_fulltext_sync", return_value="Z" * 300) as mock_ext:
        from app.services.full_text import process_fulltext
        await process_fulltext(article.id, db_session)

    mock_ext.assert_called_once_with(article.url, True)


# ---------------------------------------------------------------------------
# _sanitize_html
# ---------------------------------------------------------------------------


def test_sanitize_html_preserves_formatting():
    from app.services.full_text import _sanitize_html

    html = "<p>Hello <strong>world</strong> and <em>italic</em></p>"
    result = _sanitize_html(html, include_images=False)
    assert "<strong>world</strong>" in result
    assert "<em>italic</em>" in result
    assert "<p>" in result


def test_sanitize_html_strips_script_tags():
    from app.services.full_text import _sanitize_html

    html = "<p>Text</p><script>alert('xss')</script>"
    result = _sanitize_html(html, include_images=False)
    # bleach strips the <script> tag; text content remains but is not executable
    assert "<script>" not in result
    assert "</script>" not in result


def test_sanitize_html_strips_img_when_images_disabled():
    from app.services.full_text import _sanitize_html

    html = '<p>Text</p><img src="https://example.com/img.jpg" alt="photo">'
    result = _sanitize_html(html, include_images=False)
    assert "<img" not in result
    assert "Text" in result


def test_sanitize_html_allows_img_when_images_enabled():
    from app.services.full_text import _sanitize_html

    html = '<p>Text</p><img src="https://example.com/img.jpg" alt="photo">'
    result = _sanitize_html(html, include_images=True)
    assert "<img" in result
    assert 'src="https://example.com/img.jpg"' in result


def test_sanitize_html_strips_dangerous_img_attributes():
    from app.services.full_text import _sanitize_html

    html = '<img src="x.jpg" onerror="alert(1)" onclick="evil()">'
    result = _sanitize_html(html, include_images=True)
    assert "onerror" not in result
    assert "onclick" not in result
    assert "<img" in result


def test_sanitize_html_preserves_headings():
    from app.services.full_text import _sanitize_html

    html = "<h2>Section Title</h2><p>Content</p>"
    result = _sanitize_html(html, include_images=False)
    assert "<h2>" in result
    assert "Section Title" in result
