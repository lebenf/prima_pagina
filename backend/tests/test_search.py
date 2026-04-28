# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for GET /api/v1/search endpoint and search_service helpers."""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.models.article import Article, FulltextStatus
from app.models.feed import Feed
from app.models.user_feed import UserFeed
from app.services.search_service import _highlight_text


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def subscribed_feed(db_session, regular_user):
    feed = Feed(url="https://search-sub.example.com/rss.xml", title="Subscribed")
    db_session.add(feed)
    await db_session.flush()
    db_session.add(UserFeed(user_id=regular_user.id, feed_id=feed.id))
    await db_session.commit()
    await db_session.refresh(feed)
    return feed


@pytest.fixture
async def other_feed(db_session):
    feed = Feed(url="https://search-other.example.com/rss.xml", title="Other")
    db_session.add(feed)
    await db_session.commit()
    await db_session.refresh(feed)
    return feed


def _art(feed_id, *, title="Article", excerpt="", offset_hours=1, tags=None):
    return Article(
        feed_id=feed_id,
        guid=str(uuid4()),
        title=title,
        content_excerpt=excerpt,
        fulltext_status=FulltextStatus.PENDING.value,
        tags=tags or [],
        tags_source="none",
        published_at=datetime.utcnow() - timedelta(hours=offset_hours),
    )


@pytest.fixture
async def articles(db_session, subscribed_feed):
    arts = [
        _art(subscribed_feed.id, title="Python programming guide", excerpt="Learn Python basics"),
        _art(subscribed_feed.id, title="JavaScript tips", excerpt="Advanced JavaScript techniques"),
        _art(subscribed_feed.id, title="Cooking recipes", excerpt="Delicious Italian cooking methods"),
    ]
    for a in arts:
        db_session.add(a)
    await db_session.commit()
    return arts


@pytest.fixture
async def unsubscribed_articles(db_session, other_feed):
    arts = [
        _art(other_feed.id, title="Python secret", excerpt="Hidden python features"),
    ]
    for a in arts:
        db_session.add(a)
    await db_session.commit()
    return arts


# ---------------------------------------------------------------------------
# Unit tests: _highlight_text
# ---------------------------------------------------------------------------


def test_highlight_text_found():
    result = _highlight_text("Hello world example", "world")
    assert "<mark>world</mark>" in result


def test_highlight_text_not_found():
    result = _highlight_text("Hello there", "python")
    assert "<mark>" not in result
    assert "Hello there" in result


def test_highlight_text_truncates():
    long_text = "x" * 300
    result = _highlight_text(long_text, "missing", max_length=100)
    assert len(result) <= 104  # 100 + "…"


def test_highlight_text_ellipsis():
    text = "a" * 50 + " target " + "b" * 50 + " more text here " + "c" * 200
    result = _highlight_text(text, "target")
    assert "…" in result


def test_highlight_text_case_insensitive():
    result = _highlight_text("Hello World", "world")
    assert "<mark>" in result.lower()


def test_highlight_text_escapes_html():
    result = _highlight_text("<script>alert(1)</script>", "script")
    assert "<script>" not in result
    assert "&lt;script&gt;" in result or "<mark>" in result


def test_highlight_text_empty():
    assert _highlight_text("", "query") == ""


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


async def test_search_basic(user_client, articles):
    resp = await user_client.get("/api/v1/search?q=python")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any("python" in (item["title"] or "").lower() for item in data["items"])


async def test_search_only_subscribed(user_client, articles, unsubscribed_articles):
    resp = await user_client.get("/api/v1/search?q=python")
    assert resp.status_code == 200
    data = resp.json()
    item_ids = {item["id"] for item in data["items"]}
    # Unsubscribed article must not appear
    for ua in unsubscribed_articles:
        assert str(ua.id) not in item_ids


async def test_search_title_match(user_client, articles):
    resp = await user_client.get("/api/v1/search?q=javascript")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any("javascript" in (item["title"] or "").lower() for item in data["items"])


async def test_search_excerpt_match(user_client, articles):
    resp = await user_client.get("/api/v1/search?q=delicious")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


async def test_search_highlights_title(user_client, articles):
    resp = await user_client.get("/api/v1/search?q=python")
    assert resp.status_code == 200
    items = resp.json()["items"]
    python_items = [i for i in items if "python" in (i["title"] or "").lower()]
    assert python_items
    assert "<mark>" in (python_items[0]["title_highlighted"] or "")


async def test_search_highlights_excerpt(user_client, articles):
    resp = await user_client.get("/api/v1/search?q=delicious")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert items
    assert "<mark>" in (items[0]["excerpt_snippet"] or "")


async def test_search_empty_results(user_client, articles):
    resp = await user_client.get("/api/v1/search?q=xyzzy_nonexistent_42")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


async def test_search_min_length(user_client):
    resp = await user_client.get("/api/v1/search?q=a")
    assert resp.status_code == 422


async def test_search_filter_feed(user_client, db_session, regular_user, subscribed_feed):
    # Another subscribed feed with different content
    feed2 = Feed(url="https://search-feed2.example.com/rss.xml", title="Feed2")
    db_session.add(feed2)
    await db_session.flush()
    db_session.add(UserFeed(user_id=regular_user.id, feed_id=feed2.id))
    art = _art(feed2.id, title="exclusive python content", excerpt="only in feed2")
    db_session.add(art)
    await db_session.commit()

    # Search filtered by feed2 only
    resp = await user_client.get(f"/api/v1/search?q=python&feed_id={feed2.id}")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["feed_id"] == str(feed2.id)


async def test_search_filter_date(user_client, db_session, subscribed_feed):
    old_art = _art(
        subscribed_feed.id,
        title="old python article",
        offset_hours=200,
    )
    db_session.add(old_art)
    await db_session.commit()

    cutoff = (datetime.utcnow() - timedelta(hours=100)).isoformat()
    resp = await user_client.get(f"/api/v1/search?q=python&date_from={cutoff}")
    assert resp.status_code == 200
    # Old article should not appear
    item_ids = {item["id"] for item in resp.json()["items"]}
    assert str(old_art.id) not in item_ids


async def test_search_pagination(user_client, db_session, subscribed_feed):
    # Create 25 articles matching "pagination"
    arts = [
        _art(subscribed_feed.id, title=f"pagination test article {i}")
        for i in range(25)
    ]
    for a in arts:
        db_session.add(a)
    await db_session.commit()

    resp = await user_client.get("/api/v1/search?q=pagination&size=10&page=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 25
    assert len(data["items"]) == 10
    assert data["pages"] >= 3
    assert data["page"] == 1


async def test_search_pagination_page2(user_client, db_session, subscribed_feed):
    resp1 = await user_client.get("/api/v1/search?q=pagination&size=10&page=1")
    resp2 = await user_client.get("/api/v1/search?q=pagination&size=10&page=2")
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    ids1 = {i["id"] for i in resp1.json()["items"]}
    ids2 = {i["id"] for i in resp2.json()["items"]}
    assert ids1.isdisjoint(ids2)


async def test_search_requires_auth(client):
    resp = await client.get("/api/v1/search?q=python")
    assert resp.status_code == 401
