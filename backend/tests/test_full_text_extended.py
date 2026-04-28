# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for multi-mode full_text extraction logic."""
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.article import Article, FulltextStatus
from app.models.feed import Feed
from app.models.feed_extraction_script import FeedExtractionScript
from app.models.user_feed import UserFeed
from app.services import full_text as fulltext_svc

ARTICLE_HTML = """<html><body>
<article class="post-content">
<p>This is the main article content. It is long enough to be extracted properly.
Lorem ipsum dolor sit amet consectetur adipiscing elit.</p>
<p>More content here for the article body.</p>
</article>
</body></html>"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def feed_trafilatura(db_session):
    feed = Feed(
        url="https://trafilatura.example.com/feed.xml",
        title="Trafilatura Feed",
        fulltext_enabled=True,
        fulltext_mode="trafilatura",
    )
    db_session.add(feed)
    await db_session.commit()
    await db_session.refresh(feed)
    return feed


@pytest.fixture
async def feed_script(db_session):
    feed = Feed(
        url="https://script.example.com/feed.xml",
        title="Script Feed",
        fulltext_enabled=True,
        fulltext_mode="script",
    )
    db_session.add(feed)
    await db_session.commit()
    await db_session.refresh(feed)
    return feed


@pytest.fixture
async def feed_auto(db_session):
    feed = Feed(
        url="https://auto.example.com/feed.xml",
        title="Auto Feed",
        fulltext_enabled=True,
        fulltext_mode="auto",
    )
    db_session.add(feed)
    await db_session.commit()
    await db_session.refresh(feed)
    return feed


def _make_article(feed_id, url="https://example.com/article"):
    return Article(
        feed_id=feed_id,
        guid=str(uuid.uuid4()),
        title="Test Article",
        url=url,
        fulltext_status=FulltextStatus.PENDING.value,
        tags=[],
        tags_source="none",
        published_at=datetime.utcnow() - timedelta(hours=1),
    )


def _make_script(feed_id, selectors=None, is_active=True, consecutive_failures=0):
    return FeedExtractionScript(
        feed_id=feed_id,
        selectors=selectors or {"content": "article.post-content"},
        generated_at=datetime.utcnow(),
        validated_at=datetime.utcnow(),
        is_active=is_active,
        success_rate=1.0,
        consecutive_failures=consecutive_failures,
        sample_url="https://example.com/sample",
        sample_html_hash="abc123",
    )


# ---------------------------------------------------------------------------
# Trafilatura mode
# ---------------------------------------------------------------------------


async def test_fetch_trafilatura_mode(db_session, feed_trafilatura):
    article = _make_article(feed_trafilatura.id)
    db_session.add(article)
    await db_session.commit()

    with patch.object(fulltext_svc, "_extract_fulltext_sync", return_value="A" * 300):
        await fulltext_svc.process_fulltext(article.id, db_session)

    await db_session.refresh(article)
    assert article.fulltext_status == FulltextStatus.OK.value
    assert article.content_fulltext == "A" * 300
    assert article.fulltext_method == "trafilatura"


async def test_fetch_trafilatura_fails_on_short_content(db_session, feed_trafilatura):
    article = _make_article(feed_trafilatura.id)
    db_session.add(article)
    await db_session.commit()

    with patch.object(fulltext_svc, "_extract_fulltext_sync", return_value="short"):
        await fulltext_svc.process_fulltext(article.id, db_session)

    await db_session.refresh(article)
    assert article.fulltext_status == FulltextStatus.FAILED.value


async def test_fetch_no_url_marks_failed(db_session, feed_trafilatura):
    article = _make_article(feed_trafilatura.id, url=None)
    db_session.add(article)
    await db_session.commit()

    await fulltext_svc.process_fulltext(article.id, db_session)

    await db_session.refresh(article)
    assert article.fulltext_status == FulltextStatus.FAILED.value


# ---------------------------------------------------------------------------
# Script mode
# ---------------------------------------------------------------------------


async def test_fetch_script_mode_success(db_session, feed_script):
    article = _make_article(feed_script.id)
    db_session.add(article)
    await db_session.flush()

    script = _make_script(feed_script.id)
    db_session.add(script)
    await db_session.commit()

    with patch.object(fulltext_svc, "_download_html", return_value=ARTICLE_HTML):
        await fulltext_svc.process_fulltext(article.id, db_session)

    await db_session.refresh(article)
    assert article.fulltext_status == FulltextStatus.OK.value
    assert article.fulltext_method == "script"
    assert article.content_fulltext is not None


async def test_fetch_script_mode_fallback_on_failure(db_session, feed_script):
    article = _make_article(feed_script.id)
    db_session.add(article)
    await db_session.flush()

    # Script with selector that matches nothing
    script = _make_script(feed_script.id, selectors={"content": ".no-match"})
    db_session.add(script)
    await db_session.commit()

    with patch.object(fulltext_svc, "_download_html", return_value=ARTICLE_HTML):
        with patch.object(fulltext_svc, "_extract_fulltext_sync", return_value="B" * 300):
            await fulltext_svc.process_fulltext(article.id, db_session)

    await db_session.refresh(article)
    # In script mode (not auto), failure means no fallback — article stays failed or unset
    # The script should have incremented failures
    await db_session.refresh(script)
    assert script.consecutive_failures >= 1


async def test_fetch_script_mode_no_script_falls_back_to_trafilatura(db_session, feed_script):
    """Script mode with no script row → trafilatura fallback."""
    article = _make_article(feed_script.id)
    db_session.add(article)
    await db_session.commit()

    with patch.object(fulltext_svc, "_extract_fulltext_sync", return_value="C" * 300):
        await fulltext_svc.process_fulltext(article.id, db_session)

    await db_session.refresh(article)
    assert article.fulltext_status == FulltextStatus.OK.value
    assert article.fulltext_method == "trafilatura"


# ---------------------------------------------------------------------------
# Consecutive failure deactivation
# ---------------------------------------------------------------------------


async def test_consecutive_failures_deactivate_script(db_session, feed_script):
    article = _make_article(feed_script.id)
    db_session.add(article)
    await db_session.flush()

    script = _make_script(
        feed_script.id,
        selectors={"content": ".no-match"},
        consecutive_failures=4,  # one more will hit threshold
    )
    db_session.add(script)
    await db_session.commit()

    with patch.object(fulltext_svc, "_download_html", return_value=ARTICLE_HTML):
        with patch("asyncio.create_task"):
            await fulltext_svc._fetch_with_script(db_session, article, feed_script, script)

    await db_session.refresh(script)
    assert script.is_active is False


# ---------------------------------------------------------------------------
# Auto mode
# ---------------------------------------------------------------------------


async def test_auto_mode_uses_script_when_available(db_session, feed_auto):
    article = _make_article(feed_auto.id)
    db_session.add(article)
    await db_session.flush()

    script = _make_script(feed_auto.id)
    db_session.add(script)
    await db_session.commit()

    with patch.object(fulltext_svc, "_download_html", return_value=ARTICLE_HTML):
        await fulltext_svc.process_fulltext(article.id, db_session)

    await db_session.refresh(article)
    assert article.fulltext_status == FulltextStatus.OK.value
    assert article.fulltext_method == "script"


async def test_auto_mode_falls_back_to_trafilatura_on_script_fail(db_session, feed_auto):
    article = _make_article(feed_auto.id)
    db_session.add(article)
    await db_session.flush()

    # Script that won't match
    script = _make_script(feed_auto.id, selectors={"content": ".no-match"})
    db_session.add(script)
    await db_session.commit()

    with patch.object(fulltext_svc, "_download_html", return_value=ARTICLE_HTML):
        with patch.object(fulltext_svc, "_extract_fulltext_sync", return_value="D" * 300):
            await fulltext_svc.process_fulltext(article.id, db_session)

    await db_session.refresh(article)
    assert article.fulltext_status == FulltextStatus.OK.value
    assert article.fulltext_method == "trafilatura"


async def test_auto_mode_generates_script_on_first_article(db_session, feed_auto):
    """Auto mode with no script starts trafilatura + schedules script generation."""
    article = _make_article(feed_auto.id)
    db_session.add(article)
    await db_session.commit()

    with patch.object(fulltext_svc, "_extract_fulltext_sync", return_value="E" * 300):
        with patch("asyncio.create_task") as mock_task:
            await fulltext_svc.process_fulltext(article.id, db_session)

    await db_session.refresh(article)
    assert article.fulltext_status == FulltextStatus.OK.value
    # create_task called for script generation
    mock_task.assert_called_once()


# ---------------------------------------------------------------------------
# Layout change detection
# ---------------------------------------------------------------------------


async def test_layout_change_penalty(db_session, feed_script):
    article = _make_article(feed_script.id)
    db_session.add(article)
    await db_session.flush()

    from app.services.extraction_script import _hash_body
    html_a = ARTICLE_HTML
    html_b = "<html><body><div class='completely-different'>content</div></body></html>"

    script = _make_script(
        feed_script.id,
        selectors={"content": ".no-match"},
        consecutive_failures=0,
    )
    script.sample_html_hash = _hash_body(html_a)
    db_session.add(script)
    await db_session.commit()

    with patch.object(fulltext_svc, "_download_html", return_value=html_b):
        await fulltext_svc._fetch_with_script(db_session, article, feed_script, script)

    await db_session.refresh(script)
    # Layout change adds +2 penalty on top of normal +1 failure
    assert script.consecutive_failures >= 2


# ---------------------------------------------------------------------------
# Admin API endpoints
# ---------------------------------------------------------------------------


async def test_api_get_extraction_script_not_found(admin_client, sample_feed):
    resp = await admin_client.get(f"/api/v1/feeds/{sample_feed.id}/extraction-script")
    assert resp.status_code == 404


async def test_api_get_extraction_script(admin_client, db_session, sample_feed):
    script = _make_script(sample_feed.id)
    db_session.add(script)
    await db_session.commit()

    resp = await admin_client.get(f"/api/v1/feeds/{sample_feed.id}/extraction-script")
    assert resp.status_code == 200
    data = resp.json()
    assert data["feed_id"] == str(sample_feed.id)
    assert data["is_active"] is True


async def test_api_regenerate_script_no_articles(admin_client, sample_feed):
    resp = await admin_client.post(
        f"/api/v1/feeds/{sample_feed.id}/extraction-script/regenerate"
    )
    assert resp.status_code == 422


async def test_api_update_feed_fulltext(admin_client, db_session, sample_feed):
    resp = await admin_client.put(
        f"/api/v1/feeds/{sample_feed.id}",
        json={"fulltext_enabled": True, "fulltext_mode": "auto"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["fulltext_enabled"] is True
    assert data["fulltext_mode"] == "auto"
