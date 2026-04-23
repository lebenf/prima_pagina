# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for app/services/feed_fetcher.py"""
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import respx
from httpx import Response
from sqlalchemy import select

from app.models.article import Article
from app.models.feed import Feed
from app.services.feed_fetcher import (
    _handle_fetch_error,
    _is_feed_due,
    fetch_feed,
)

# ---------------------------------------------------------------------------
# Test fixtures (XML)
# ---------------------------------------------------------------------------

SAMPLE_FEED_XML = (Path(__file__).parent / "fixtures" / "sample_feed.xml").read_text()

FEED_WITHOUT_GUIDS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>No GUID Feed</title>
    <link>https://noguid.example.com</link>
    <item>
      <title>Article Without GUID</title>
      <link>https://noguid.example.com/1</link>
      <description>Content without a guid element.</description>
    </item>
  </channel>
</rss>
"""

FEED_WITH_SCRIPT_TAGS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>XSS Feed</title>
    <link>https://xss.example.com</link>
    <item>
      <title>Malicious Article</title>
      <guid>xss-article-001</guid>
      <link>https://xss.example.com/1</link>
      <description>&lt;p&gt;Safe content.&lt;/p&gt;&lt;script&gt;alert('xss')&lt;/script&gt;&lt;iframe src="evil.com"&gt;&lt;/iframe&gt;</description>
    </item>
  </channel>
</rss>
"""

FEED_ITALIAN_CONTENT = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Italian Feed</title>
    <link>https://it.example.com</link>
    <item>
      <title>Notizie italiane</title>
      <guid>italian-article-001</guid>
      <link>https://it.example.com/1</link>
      <description>Il governo italiano ha approvato il nuovo decreto legge sulla sicurezza nazionale e la protezione dei dati personali dei cittadini italiani.</description>
    </item>
  </channel>
</rss>
"""

FEED_WITH_TIMEZONE = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Timezone Feed</title>
    <link>https://tz.example.com</link>
    <item>
      <title>Article With Timezone</title>
      <guid>tz-article-001</guid>
      <link>https://tz.example.com/1</link>
      <pubDate>Wed, 15 Apr 2026 10:00:00 +0200</pubDate>
      <description>Article with a non-UTC timezone.</description>
    </item>
  </channel>
</rss>
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@respx.mock
async def test_fetch_new_articles(db_session, sample_feed):
    """Fetching a valid RSS feed inserts all new articles."""
    respx.get(sample_feed.url).mock(return_value=Response(200, text=SAMPLE_FEED_XML))

    count = await fetch_feed(sample_feed.id, db_session)

    assert count == 3
    result = await db_session.execute(
        select(Article).where(Article.feed_id == sample_feed.id)
    )
    articles = result.scalars().all()
    assert len(articles) == 3
    titles = {a.title for a in articles}
    assert "First Article" in titles
    assert "Second Article" in titles
    assert "Third Article" in titles


@respx.mock
async def test_no_duplicate_on_second_fetch(db_session, sample_feed):
    """Re-fetching the same feed does not create duplicate articles."""
    respx.get(sample_feed.url).mock(return_value=Response(200, text=SAMPLE_FEED_XML))

    first_count = await fetch_feed(sample_feed.id, db_session)
    assert first_count == 3

    # Second fetch with same content — reset the mock to serve again
    respx.get(sample_feed.url).mock(return_value=Response(200, text=SAMPLE_FEED_XML))
    second_count = await fetch_feed(sample_feed.id, db_session)
    assert second_count == 0

    result = await db_session.execute(
        select(Article).where(Article.feed_id == sample_feed.id)
    )
    assert len(result.scalars().all()) == 3


@respx.mock
async def test_304_no_insert(db_session, sample_feed):
    """A 304 Not Modified response updates last_fetched_at but inserts no articles."""
    respx.get(sample_feed.url).mock(return_value=Response(304))

    count = await fetch_feed(sample_feed.id, db_session)

    assert count == 0
    await db_session.refresh(sample_feed)
    assert sample_feed.last_fetched_at is not None
    assert sample_feed.error_count == 0

    result = await db_session.execute(
        select(Article).where(Article.feed_id == sample_feed.id)
    )
    assert len(result.scalars().all()) == 0


@respx.mock
async def test_etag_sent_in_request(db_session, sample_feed):
    """If the feed has a stored ETag, it is sent as If-None-Match in the next request."""
    sample_feed.last_etag = '"abc123"'
    await db_session.commit()

    captured_headers = {}

    def capture_request(request):
        captured_headers.update(dict(request.headers))
        return Response(200, text=SAMPLE_FEED_XML)

    respx.get(sample_feed.url).mock(side_effect=capture_request)
    await fetch_feed(sample_feed.id, db_session)

    assert captured_headers.get("if-none-match") == '"abc123"'


@respx.mock
async def test_http_error_increments_error_count(db_session, sample_feed):
    """An HTTP 500 response increments error_count and sets next_fetch_at."""
    respx.get(sample_feed.url).mock(return_value=Response(500))

    initial_error_count = sample_feed.error_count
    await fetch_feed(sample_feed.id, db_session)

    await db_session.refresh(sample_feed)
    assert sample_feed.error_count == initial_error_count + 1
    assert sample_feed.last_status == 500
    assert sample_feed.next_fetch_at is not None
    assert sample_feed.next_fetch_at > datetime.utcnow()


@respx.mock
async def test_feed_disabled_after_10_errors(db_session, sample_feed):
    """After 10 consecutive errors the feed is automatically disabled."""
    sample_feed.error_count = 9
    await db_session.commit()

    respx.get(sample_feed.url).mock(return_value=Response(503))
    await fetch_feed(sample_feed.id, db_session)

    await db_session.refresh(sample_feed)
    assert sample_feed.error_count == 10
    assert sample_feed.is_active is False


async def test_backoff_calculation(db_session, sample_feed):
    """Backoff is exponential and capped at 1440 minutes."""
    sample_feed.fetch_interval_min = 60
    sample_feed.error_count = 0
    await db_session.commit()

    before = datetime.utcnow()
    await _handle_fetch_error(sample_feed, db_session, 500, "Server Error")
    after = datetime.utcnow()

    await db_session.refresh(sample_feed)
    assert sample_feed.error_count == 1
    # backoff = min(60 * 2^1, 1440) = 120 minutes
    expected_lower = before + timedelta(minutes=119)
    expected_upper = after + timedelta(minutes=121)
    assert expected_lower < sample_feed.next_fetch_at < expected_upper

    # Verify cap: error_count=10 → 60 * 2^10 = 61440 → capped at 1440
    sample_feed.error_count = 10
    await db_session.commit()
    await _handle_fetch_error(sample_feed, db_session, 500, "Server Error")
    await db_session.refresh(sample_feed)
    # next_fetch_at should be ~1440 minutes from now, not 61440
    upper_cap = datetime.utcnow() + timedelta(minutes=1441)
    assert sample_feed.next_fetch_at < upper_cap


@respx.mock
async def test_html_sanitization(db_session):
    """Script and iframe tags are stripped from article content."""
    feed = Feed(url="https://xss.example.com/feed.xml", title="XSS Test Feed")
    db_session.add(feed)
    await db_session.commit()
    await db_session.refresh(feed)

    respx.get(feed.url).mock(return_value=Response(200, text=FEED_WITH_SCRIPT_TAGS))
    await fetch_feed(feed.id, db_session)

    result = await db_session.execute(
        select(Article).where(Article.feed_id == feed.id)
    )
    article = result.scalars().first()
    assert article is not None
    assert "<script>" not in (article.content_excerpt or "")
    assert "alert(" not in (article.content_excerpt or "")
    assert "<iframe" not in (article.content_excerpt or "")
    assert "Safe content." in (article.content_excerpt or "")


@respx.mock
async def test_guid_fallback_hash(db_session):
    """When a feed entry has no guid element, a hash of link+title is used."""
    feed = Feed(url="https://noguid.example.com/feed.xml", title="No GUID Feed")
    db_session.add(feed)
    await db_session.commit()
    await db_session.refresh(feed)

    respx.get(feed.url).mock(return_value=Response(200, text=FEED_WITHOUT_GUIDS))
    count = await fetch_feed(feed.id, db_session)

    assert count == 1
    result = await db_session.execute(
        select(Article).where(Article.feed_id == feed.id)
    )
    article = result.scalars().first()
    assert article is not None
    # GUID should be a 64-char hex hash (sha256 truncated)
    assert len(article.guid) == 64
    assert all(c in "0123456789abcdef" for c in article.guid)


@respx.mock
async def test_language_detection(db_session):
    """Language is detected from article content when not set in the feed."""
    feed = Feed(url="https://it.example.com/feed.xml", title="Italian Feed")
    db_session.add(feed)
    await db_session.commit()
    await db_session.refresh(feed)

    respx.get(feed.url).mock(return_value=Response(200, text=FEED_ITALIAN_CONTENT))
    await fetch_feed(feed.id, db_session)

    result = await db_session.execute(
        select(Article).where(Article.feed_id == feed.id)
    )
    article = result.scalars().first()
    assert article is not None
    # Language should be detected as Italian
    assert article.language == "it"


@respx.mock
async def test_published_at_utc_normalization(db_session):
    """published_at is stored as a naive UTC datetime regardless of the feed timezone."""
    feed = Feed(url="https://tz.example.com/feed.xml", title="Timezone Feed")
    db_session.add(feed)
    await db_session.commit()
    await db_session.refresh(feed)

    respx.get(feed.url).mock(return_value=Response(200, text=FEED_WITH_TIMEZONE))
    await fetch_feed(feed.id, db_session)

    result = await db_session.execute(
        select(Article).where(Article.feed_id == feed.id)
    )
    article = result.scalars().first()
    assert article is not None
    assert article.published_at is not None
    # +0200 offset: 10:00:00+02:00 → 08:00:00 UTC
    assert article.published_at.hour == 8
    assert article.published_at.tzinfo is None  # stored as naive UTC
