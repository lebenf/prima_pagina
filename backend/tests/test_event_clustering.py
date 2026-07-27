# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for app/services/event_clustering.py."""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.article import Article
from app.models.event import Event, EventStatus, TitleSource
from app.models.feed import Feed
from app.services.event_clustering import (
    attach_or_create_event,
    close_stale_events,
    find_candidate_events,
)


def _make_article(feed_id, tags=None, category_id=None, title="Article", published_at=None):
    art = Article(
        feed_id=feed_id,
        guid=str(uuid4()),
        title=title,
        tags=tags or [],
        tags_source="llm" if tags else "none",
        published_at=published_at or datetime.utcnow(),
    )
    return art


def _make_event(category_id=None, tags=None, last_activity_at=None, status=EventStatus.OPEN.value,
                 title="Existing event", article_count=1, source_count=1):
    return Event(
        title=title,
        title_source=TitleSource.REPRESENTATIVE.value,
        tags=tags or [],
        category_id=category_id,
        status=status,
        article_count=article_count,
        source_count=source_count,
        opened_at=datetime.utcnow() - timedelta(hours=1),
        last_activity_at=last_activity_at or datetime.utcnow(),
    )


@pytest.fixture
async def feed_a(db_session):
    f = Feed(url="https://event-feed-a.example.com/rss.xml", title="Feed A")
    db_session.add(f)
    await db_session.commit()
    await db_session.refresh(f)
    return f


@pytest.fixture
async def feed_b(db_session):
    f = Feed(url="https://event-feed-b.example.com/rss.xml", title="Feed B")
    db_session.add(f)
    await db_session.commit()
    await db_session.refresh(f)
    return f


@pytest.fixture
async def category_a(db_session):
    from app.models.category import Category
    cat = Category(slug="world-events", name={"it": "Mondo", "en": "World"})
    db_session.add(cat)
    await db_session.commit()
    await db_session.refresh(cat)
    return cat


# ---------------------------------------------------------------------------
# find_candidate_events
# ---------------------------------------------------------------------------


async def test_no_candidates_when_no_open_events(db_session, feed_a, category_a):
    article = _make_article(feed_a.id, tags=["ai"])
    candidates = await find_candidate_events(db_session, article, category_a.id)
    assert candidates == []


async def test_candidate_requires_tag_overlap(db_session, feed_a, category_a):
    event = _make_event(category_id=category_a.id, tags=["sports", "football"])
    db_session.add(event)
    await db_session.commit()

    article = _make_article(feed_a.id, tags=["ai", "tech"])
    candidates = await find_candidate_events(db_session, article, category_a.id)
    assert candidates == []


async def test_candidate_matches_on_tag_overlap(db_session, feed_a, category_a):
    event = _make_event(category_id=category_a.id, tags=["ai", "tech"])
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    article = _make_article(feed_a.id, tags=["ai"])
    candidates = await find_candidate_events(db_session, article, category_a.id)
    assert len(candidates) == 1
    assert candidates[0].id == event.id


async def test_candidate_excluded_when_stale(db_session, feed_a, category_a):
    stale_event = _make_event(
        category_id=category_a.id, tags=["ai"],
        last_activity_at=datetime.utcnow() - timedelta(hours=200),
    )
    db_session.add(stale_event)
    await db_session.commit()

    article = _make_article(feed_a.id, tags=["ai"])
    candidates = await find_candidate_events(db_session, article, category_a.id)
    assert candidates == []


async def test_candidate_excluded_when_closed(db_session, feed_a, category_a):
    closed_event = _make_event(category_id=category_a.id, tags=["ai"], status=EventStatus.CLOSED.value)
    db_session.add(closed_event)
    await db_session.commit()

    article = _make_article(feed_a.id, tags=["ai"])
    candidates = await find_candidate_events(db_session, article, category_a.id)
    assert candidates == []


# ---------------------------------------------------------------------------
# attach_or_create_event
# ---------------------------------------------------------------------------


async def test_new_article_creates_event_when_no_candidates(db_session, feed_a, category_a):
    article = _make_article(feed_a.id, tags=["ai"], title="Breaking news")
    db_session.add(article)
    await db_session.flush()
    article.feed = await db_session.get(Feed, feed_a.id)

    event, should_regen = await attach_or_create_event(db_session, article, provider=None)

    assert event.article_count == 1
    assert event.source_count == 1
    assert event.title_source == TitleSource.REPRESENTATIVE.value
    assert event.title == "Breaking news"
    assert article.event_id == event.id
    assert article.event_role == "seed"
    assert should_regen is False


async def test_article_attaches_to_matching_candidate_via_llm(db_session, feed_a, feed_b, category_a):
    event = _make_event(category_id=category_a.id, tags=["ai"])
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    feed_b.category_id = category_a.id
    article = _make_article(feed_b.id, tags=["ai", "startup"])
    db_session.add(article)
    await db_session.flush()
    article.feed = feed_b

    mock_provider = AsyncMock()
    mock_provider.generate_text = AsyncMock(return_value='{"event_index": 1}')

    result_event, should_regen = await attach_or_create_event(db_session, article, provider=mock_provider)

    assert result_event.id == event.id
    assert article.event_id == event.id
    assert article.event_role == "member"
    assert result_event.article_count == 2
    assert set(result_event.tags) == {"ai", "startup"}
    assert should_regen is True  # new source joined


async def test_llm_says_no_match_creates_new_event(db_session, feed_a, feed_b, category_a):
    event = _make_event(category_id=category_a.id, tags=["ai"])
    db_session.add(event)
    await db_session.commit()

    feed_b.category_id = category_a.id
    article = _make_article(feed_b.id, tags=["ai"])
    db_session.add(article)
    await db_session.flush()
    article.feed = feed_b

    mock_provider = AsyncMock()
    mock_provider.generate_text = AsyncMock(return_value='{"event_index": null}')

    result_event, should_regen = await attach_or_create_event(db_session, article, provider=mock_provider)

    assert result_event.id != event.id
    assert result_event.article_count == 1


async def test_llm_failure_falls_back_to_new_event_when_multiple_candidates(db_session, feed_a, feed_b, category_a):
    event1 = _make_event(category_id=category_a.id, tags=["ai"], title="Event 1")
    event2 = _make_event(category_id=category_a.id, tags=["ai"], title="Event 2")
    db_session.add_all([event1, event2])
    await db_session.commit()

    feed_b.category_id = category_a.id
    article = _make_article(feed_b.id, tags=["ai"])
    db_session.add(article)
    await db_session.flush()
    article.feed = feed_b

    mock_provider = AsyncMock()
    mock_provider.generate_text = AsyncMock(return_value="not valid json")

    result_event, _ = await attach_or_create_event(db_session, article, provider=mock_provider)

    assert result_event.id not in (event1.id, event2.id)


async def test_source_count_reflects_distinct_feeds(db_session, feed_a, feed_b, category_a):
    article1 = _make_article(feed_a.id, tags=["ai"])
    db_session.add(article1)
    await db_session.flush()
    article1.feed = await db_session.get(Feed, feed_a.id)
    event, _ = await attach_or_create_event(db_session, article1, provider=None)
    await db_session.commit()
    assert event.source_count == 1

    article2 = _make_article(feed_b.id, tags=["ai"])
    db_session.add(article2)
    await db_session.flush()
    article2.feed = await db_session.get(Feed, feed_b.id)

    mock_provider = AsyncMock()
    mock_provider.generate_text = AsyncMock(return_value='{"event_index": 1}')
    result_event, _ = await attach_or_create_event(db_session, article2, provider=mock_provider)

    assert result_event.id == event.id
    assert result_event.source_count == 2


async def test_regen_not_triggered_on_third_article_same_source(db_session, feed_a, category_a):
    """Two articles from the SAME feed attached to an event should not trigger
    is_new_source; only the every-3rd-article condition should fire."""
    feed_a.category_id = category_a.id
    event = _make_event(category_id=category_a.id, tags=["ai"], article_count=2, source_count=1)
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    # Simulate 2 prior articles from feed_a already attached
    prior1 = _make_article(feed_a.id, tags=["ai"])
    prior2 = _make_article(feed_a.id, tags=["ai"])
    prior1.event_id = event.id
    prior2.event_id = event.id
    db_session.add_all([prior1, prior2])
    await db_session.commit()

    article = _make_article(feed_a.id, tags=["ai"])
    db_session.add(article)
    await db_session.flush()
    article.feed = feed_a

    mock_provider = AsyncMock()
    mock_provider.generate_text = AsyncMock(return_value='{"event_index": 1}')
    result_event, should_regen = await attach_or_create_event(db_session, article, provider=mock_provider)

    assert result_event.article_count == 3
    assert should_regen is True  # 3rd article, even from the same source


# ---------------------------------------------------------------------------
# close_stale_events
# ---------------------------------------------------------------------------


async def test_close_stale_events_closes_only_expired(db_session, category_a):
    stale = _make_event(category_id=category_a.id, tags=["ai"], last_activity_at=datetime.utcnow() - timedelta(hours=100))
    fresh = _make_event(category_id=category_a.id, tags=["ai"], last_activity_at=datetime.utcnow() - timedelta(hours=1))
    db_session.add_all([stale, fresh])
    await db_session.commit()
    await db_session.refresh(stale)
    await db_session.refresh(fresh)

    count = await close_stale_events(db_session)

    await db_session.refresh(stale)
    await db_session.refresh(fresh)
    assert count == 1
    assert stale.status == EventStatus.CLOSED.value
    assert stale.closed_at is not None
    assert fresh.status == EventStatus.OPEN.value
