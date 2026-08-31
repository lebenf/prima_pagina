# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for app/services/event_clustering.py."""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from collections import Counter

from app.models.article import Article
from app.models.event import Event, EventStatus, TitleSource
from app.models.feed import Feed
from app.services.event_clustering import (
    EVENT_LARGE_SIZE_THRESHOLD,
    _derive_event_tags,
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


async def test_zero_overlap_still_candidate_below_large_threshold(db_session, feed_a, category_a):
    """No tag overlap no longer excludes a small/medium event — the (already
    conservative) LLM match step is the real filter, not tag overlap. This is
    what lets two differently-tagged articles about the same real story still
    get merged instead of spawning a duplicate event."""
    event = _make_event(category_id=category_a.id, tags=["sports", "football"])
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    article = _make_article(feed_a.id, tags=["ai", "tech"])
    candidates = await find_candidate_events(db_session, article, category_a.id)
    assert len(candidates) == 1
    assert candidates[0].id == event.id


async def test_large_event_excluded_when_weak_overlap_ratio(db_session, feed_a, category_a):
    large_event = _make_event(
        category_id=category_a.id, tags=["politica"], article_count=EVENT_LARGE_SIZE_THRESHOLD,
    )
    db_session.add(large_event)
    await db_session.commit()
    await db_session.refresh(large_event)

    # 1 of 2 tags overlap -> ratio 0.5, at the threshold (>=): included
    at_threshold = _make_article(feed_a.id, tags=["politica", "estero"])
    candidates = await find_candidate_events(db_session, at_threshold, category_a.id)
    assert len(candidates) == 1

    # 1 of 3 tags overlap -> ratio 0.33, below threshold: excluded
    below_threshold = _make_article(feed_a.id, tags=["politica", "estero", "sport"])
    candidates2 = await find_candidate_events(db_session, below_threshold, category_a.id)
    assert candidates2 == []


async def test_large_event_included_with_strong_overlap_ratio(db_session, feed_a, category_a):
    large_event = _make_event(
        category_id=category_a.id, tags=["politica", "elezioni"],
        article_count=EVENT_LARGE_SIZE_THRESHOLD,
    )
    db_session.add(large_event)
    await db_session.commit()
    await db_session.refresh(large_event)

    article = _make_article(feed_a.id, tags=["politica", "elezioni"])
    candidates = await find_candidate_events(db_session, article, category_a.id)
    assert len(candidates) == 1
    assert candidates[0].id == large_event.id


# ---------------------------------------------------------------------------
# _derive_event_tags
# ---------------------------------------------------------------------------


def test_derive_event_tags_prunes_one_off_tags_on_large_event():
    counts = Counter({"politica": 27, "elezioni": 27, "superman": 1, "gaza": 1})
    result = _derive_event_tags(counts, article_count=89)
    assert "superman" not in result
    assert "gaza" not in result
    assert "politica" in result
    assert "elezioni" in result


def test_derive_event_tags_keeps_all_founding_tags_for_new_event():
    counts = Counter({"ai": 1, "startup": 1})
    result = _derive_event_tags(counts, article_count=1)
    assert set(result) == {"ai", "startup"}


def test_derive_event_tags_caps_at_max_size():
    counts = Counter({f"tag{i}": 20 for i in range(20)})
    result = _derive_event_tags(counts, article_count=20)
    assert len(result) == 12


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

    # Enough headroom for a reasoning model's hidden chain-of-thought before
    # the JSON answer, and json_mode requested where the provider supports it.
    mock_provider.generate_text.assert_called_once()
    call_kwargs = mock_provider.generate_text.call_args.kwargs
    assert call_kwargs["max_tokens"] == 600
    assert call_kwargs["json_mode"] is True


async def test_llm_match_tolerates_fenced_json_response(db_session, feed_a, feed_b, category_a):
    """A model that wraps its JSON in a markdown code fence despite being
    told not to must still match — this is exactly the robustness gap that
    made clustering swing wildly between models."""
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
    mock_provider.generate_text = AsyncMock(return_value='```json\n{"event_index": 1}\n```')

    result_event, _ = await attach_or_create_event(db_session, article, provider=mock_provider)

    assert result_event.id == event.id


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


async def test_attach_prunes_one_off_tag_after_several_members(db_session, feed_a, feed_b, category_a):
    """A tag introduced by only one article among several members must not
    survive in the event's derived `tags` — this is what stops a grab-bag
    event from keeping generic/noise tags forever."""
    feed_a.category_id = category_a.id
    feed_b.category_id = category_a.id

    seed = _make_article(feed_a.id, tags=["politica"])
    db_session.add(seed)
    await db_session.flush()
    seed.feed = feed_a
    event, _ = await attach_or_create_event(db_session, seed, provider=None)
    await db_session.commit()
    await db_session.refresh(event)

    mock_provider = AsyncMock()
    mock_provider.generate_text = AsyncMock(return_value='{"event_index": 1}')

    for tags in (["politica"], ["politica"], ["politica", "superman"]):
        art = _make_article(feed_b.id, tags=tags)
        db_session.add(art)
        await db_session.flush()
        art.feed = feed_b
        event, _ = await attach_or_create_event(db_session, art, provider=mock_provider)
        await db_session.commit()
        await db_session.refresh(event)

    assert "politica" in event.tags
    assert "superman" not in event.tags


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
