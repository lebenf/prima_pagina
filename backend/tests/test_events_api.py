# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for /api/v1/events/* endpoints and admin event-correction endpoints."""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.models.article import Article
from app.models.category import Category
from app.models.event import Event, EventStatus, TitleSource
from app.models.feed import Feed
from app.models.user_topic_preference import UserTopicPreference


def _make_event(category_id=None, tags=None, article_count=1, source_count=1, title="Event"):
    return Event(
        title=title,
        title_source=TitleSource.REPRESENTATIVE.value,
        synopsis="Synopsis text",
        tags=tags or [],
        category_id=category_id,
        status=EventStatus.OPEN.value,
        article_count=article_count,
        source_count=source_count,
        opened_at=datetime.utcnow() - timedelta(hours=2),
        last_activity_at=datetime.utcnow() - timedelta(hours=1),
    )


def _make_article(feed_id, event_id=None, tags=None, role=None, title="Article"):
    return Article(
        feed_id=feed_id,
        guid=str(uuid4()),
        title=title,
        url=f"https://example.com/{uuid4()}",
        tags=tags or [],
        tags_source="llm" if tags else "none",
        published_at=datetime.utcnow() - timedelta(hours=1),
        event_id=event_id,
        event_role=role,
    )


@pytest.fixture
async def feed(db_session):
    f = Feed(url="https://events-api-test.example.com/feed.xml", title="Events Feed")
    db_session.add(f)
    await db_session.commit()
    await db_session.refresh(f)
    return f


@pytest.fixture
async def category(db_session):
    cat = Category(slug="events-cat", name={"it": "Eventi", "en": "Events"})
    db_session.add(cat)
    await db_session.commit()
    await db_session.refresh(cat)
    return cat


@pytest.fixture
async def event_with_article(db_session, feed, category):
    event = _make_event(category_id=category.id, tags=["ai", "tech"], article_count=1)
    db_session.add(event)
    await db_session.flush()
    article = _make_article(feed.id, event_id=event.id, tags=["ai", "tech"], role="seed")
    db_session.add(article)
    await db_session.commit()
    await db_session.refresh(event)
    await db_session.refresh(article)
    return event, article


# ---------------------------------------------------------------------------
# GET /events (flat paginated chronological list)
# ---------------------------------------------------------------------------


async def test_list_events_empty(user_client):
    resp = await user_client.get("/api/v1/events")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["pages"] == 1


async def test_list_events_chronological_order(user_client, db_session, category):
    older = _make_event(category_id=category.id, title="Older")
    older.last_activity_at = datetime.utcnow() - timedelta(hours=5)
    newer = _make_event(category_id=category.id, title="Newer")
    newer.last_activity_at = datetime.utcnow() - timedelta(minutes=10)
    db_session.add_all([older, newer])
    await db_session.commit()

    resp = await user_client.get("/api/v1/events")
    assert resp.status_code == 200
    titles = [item["title"] for item in resp.json()["items"]]
    assert titles == ["Newer", "Older"]


async def test_list_events_pagination(user_client, db_session, category):
    for i in range(3):
        event = _make_event(category_id=category.id, title=f"Event {i}")
        event.last_activity_at = datetime.utcnow() - timedelta(minutes=i)
        db_session.add(event)
    await db_session.commit()

    resp = await user_client.get("/api/v1/events", params={"page": 1, "size": 2})
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["pages"] == 2

    resp2 = await user_client.get("/api/v1/events", params={"page": 2, "size": 2})
    assert len(resp2.json()["items"]) == 1


async def test_list_events_filters_by_category(user_client, db_session, category):
    from app.models.category import Category
    other_category = Category(slug="other-cat", name={"it": "Altro", "en": "Other"})
    db_session.add(other_category)
    await db_session.flush()

    matching = _make_event(category_id=category.id, title="Matching")
    other = _make_event(category_id=other_category.id, title="Other")
    db_session.add_all([matching, other])
    await db_session.commit()

    resp = await user_client.get("/api/v1/events", params={"category_id": str(category.id)})
    titles = [item["title"] for item in resp.json()["items"]]
    assert titles == ["Matching"]


async def test_list_events_filters_by_status(user_client, db_session, category):
    open_event = _make_event(category_id=category.id, title="Open one")
    closed_event = _make_event(category_id=category.id, title="Closed one")
    closed_event.status = EventStatus.CLOSED.value
    db_session.add_all([open_event, closed_event])
    await db_session.commit()

    resp = await user_client.get("/api/v1/events", params={"status": "closed"})
    titles = [item["title"] for item in resp.json()["items"]]
    assert titles == ["Closed one"]


async def test_list_events_requires_auth(client):
    resp = await client.get("/api/v1/events")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /events/frontpage
# ---------------------------------------------------------------------------


async def test_frontpage_empty_when_no_events(user_client):
    resp = await user_client.get("/api/v1/events/frontpage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hero"] is None
    assert data["second_row"] == []
    assert data["columns"] == []


async def test_frontpage_returns_event_as_hero(user_client, event_with_article):
    event, _ = event_with_article
    resp = await user_client.get("/api/v1/events/frontpage")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hero"] is not None
    assert data["hero"]["id"] == str(event.id)
    assert data["hero"]["source_count"] == 1


async def test_frontpage_requires_auth(client):
    resp = await client.get("/api/v1/events/frontpage")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /events/{id}
# ---------------------------------------------------------------------------


async def test_get_event_detail(user_client, event_with_article):
    event, article = event_with_article
    resp = await user_client.get(f"/api/v1/events/{event.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(event.id)
    assert len(data["articles"]) == 1
    assert data["articles"][0]["id"] == str(article.id)


async def test_get_event_not_found(user_client):
    resp = await user_client.get(f"/api/v1/events/{uuid4()}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST/DELETE /events/{id}/vote
# ---------------------------------------------------------------------------


async def test_vote_event_updates_all_member_tags(user_client, db_session, event_with_article, regular_user):
    event, _ = event_with_article
    resp = await user_client.post(f"/api/v1/events/{event.id}/vote", json={"vote": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["vote"] == 1
    assert set(data["topic_scores_updated"]) == {"ai", "tech"}

    for tag in ("ai", "tech"):
        pref = await db_session.get(UserTopicPreference, (regular_user.id, tag))
        assert pref is not None
        assert pref.score > 0


async def test_unvote_event_reverts_topic_scores(user_client, db_session, event_with_article, regular_user):
    event, _ = event_with_article
    await user_client.post(f"/api/v1/events/{event.id}/vote", json={"vote": 1})

    resp = await user_client.delete(f"/api/v1/events/{event.id}/vote")
    assert resp.status_code == 200
    assert resp.json()["vote"] == 0

    for tag in ("ai", "tech"):
        pref = await db_session.get(UserTopicPreference, (regular_user.id, tag))
        assert pref.score == pytest.approx(0.0)


async def test_vote_event_requires_auth(client, event_with_article):
    event, _ = event_with_article
    resp = await client.post(f"/api/v1/events/{event.id}/vote", json={"vote": 1})
    assert resp.status_code == 401


async def test_vote_event_not_found(user_client):
    resp = await user_client.post(f"/api/v1/events/{uuid4()}/vote", json={"vote": 1})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Admin: merge / detach / regenerate-summary
# ---------------------------------------------------------------------------


@pytest.fixture
async def two_events_with_articles(db_session, feed, category):
    event1 = _make_event(category_id=category.id, tags=["ai"], article_count=1)
    event2 = _make_event(category_id=category.id, tags=["startup"], article_count=1, title="Event 2")
    db_session.add_all([event1, event2])
    await db_session.flush()

    art1 = _make_article(feed.id, event_id=event1.id, tags=["ai"], role="seed", title="Article 1")
    art2 = _make_article(feed.id, event_id=event2.id, tags=["startup"], role="seed", title="Article 2")
    db_session.add_all([art1, art2])
    await db_session.commit()
    await db_session.refresh(event1)
    await db_session.refresh(event2)
    return event1, event2, art1, art2


async def test_merge_events_moves_members_and_deletes_source(admin_client, db_session, two_events_with_articles):
    event1, event2, art1, art2 = two_events_with_articles
    event1_id, event2_id, art2_id = event1.id, event2.id, art2.id

    resp = await admin_client.post(
        f"/api/v1/admin/events/{event2_id}/merge",
        json={"target_event_id": str(event1_id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(event1_id)
    assert set(data["tags"]) == {"ai", "startup"}
    assert data["article_count"] == 2
    assert len(data["articles"]) == 2

    db_session.expire_all()  # event2/art2 were cached before the API call committed elsewhere
    deleted = await db_session.get(Event, event2_id)
    assert deleted is None

    art2_reloaded = await db_session.get(Article, art2_id)
    assert art2_reloaded.event_id == event1_id


async def test_merge_events_rejects_self_merge(admin_client, event_with_article):
    event, _ = event_with_article
    resp = await admin_client.post(
        f"/api/v1/admin/events/{event.id}/merge",
        json={"target_event_id": str(event.id)},
    )
    assert resp.status_code == 400


async def test_detach_article_creates_new_single_event(admin_client, db_session, feed, category):
    event = _make_event(category_id=category.id, tags=["ai", "tech"], article_count=2, source_count=1)
    db_session.add(event)
    await db_session.flush()
    art1 = _make_article(feed.id, event_id=event.id, tags=["ai"], role="seed", title="A1")
    art2 = _make_article(feed.id, event_id=event.id, tags=["tech"], role="member", title="A2")
    db_session.add_all([art1, art2])
    await db_session.commit()
    await db_session.refresh(art2)

    resp = await admin_client.post(f"/api/v1/admin/events/{event.id}/detach/{art2.id}")
    assert resp.status_code == 200

    await db_session.refresh(art2)
    assert art2.event_id != event.id
    assert art2.event_role == "seed"

    new_event = await db_session.get(Event, art2.event_id)
    assert new_event is not None
    assert new_event.article_count == 1

    await db_session.refresh(event)
    assert event.article_count == 1
    assert event.tags == ["ai"]


async def test_admin_endpoints_reject_non_admin(user_client, event_with_article):
    event, _ = event_with_article
    resp = await user_client.post(
        f"/api/v1/admin/events/{event.id}/merge", json={"target_event_id": str(uuid4())}
    )
    assert resp.status_code == 403

    resp = await user_client.post(f"/api/v1/admin/events/{event.id}/detach/{uuid4()}")
    assert resp.status_code == 403

    resp = await user_client.post(f"/api/v1/admin/events/{event.id}/regenerate-summary")
    assert resp.status_code == 403


async def test_regenerate_summary_admin_forced(admin_client, event_with_article, monkeypatch):
    from unittest.mock import AsyncMock
    import app.api.admin as admin_module

    mock_regen = AsyncMock(return_value=None)
    monkeypatch.setattr("app.services.event_summary_service.regenerate_event_summary", mock_regen)

    event, _ = event_with_article
    resp = await admin_client.post(f"/api/v1/admin/events/{event.id}/regenerate-summary")
    assert resp.status_code == 200
    mock_regen.assert_awaited_once_with(event.id)
