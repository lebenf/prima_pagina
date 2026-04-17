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


async def _make_article(db_session, *, url="https://example.com/article", status=FulltextStatus.PENDING.value):
    feed = Feed(url=f"https://example.com/{uuid4()}/feed.xml", title="Test Feed")
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
# Tests
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
