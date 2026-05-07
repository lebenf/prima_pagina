# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest

from app.models.feed import Feed
from app.models.user_feed import UserFeed


# ---------------------------------------------------------------------------
# Test-local fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def sample_feeds(db_session):
    feeds = [
        Feed(url=f"https://feed{i}.example.com/rss.xml", title=f"Feed {i}")
        for i in range(3)
    ]
    for f in feeds:
        db_session.add(f)
    await db_session.commit()
    for f in feeds:
        await db_session.refresh(f)
    return feeds


@pytest.fixture
async def subscribed_feed(db_session, sample_feed, regular_user):
    uf = UserFeed(user_id=regular_user.id, feed_id=sample_feed.id)
    db_session.add(uf)
    await db_session.commit()
    return sample_feed


@pytest.fixture
async def subscribed_feeds(db_session, sample_feeds, regular_user):
    for feed in sample_feeds:
        uf = UserFeed(user_id=regular_user.id, feed_id=feed.id)
        db_session.add(uf)
    await db_session.commit()
    return sample_feeds


@pytest.fixture
async def feeds_by_category(db_session, category, another_category):
    f1 = Feed(url="https://cat1.example.com/rss.xml", title="Cat1 Feed", category_id=category.id)
    f2 = Feed(url="https://cat2.example.com/rss.xml", title="Cat2 Feed", category_id=another_category.id)
    f3 = Feed(url="https://nocat.example.com/rss.xml", title="NoCat Feed")
    for f in (f1, f2, f3):
        db_session.add(f)
    await db_session.commit()
    for f in (f1, f2, f3):
        await db_session.refresh(f)
    return {"category": f1, "another_category": f2, "no_category": f3}


# ---------------------------------------------------------------------------
# List feeds
# ---------------------------------------------------------------------------


async def test_list_feeds_unauthenticated(client):
    resp = await client.get("/api/v1/feeds")
    assert resp.status_code == 401


async def test_list_feeds_authenticated(user_client, sample_feeds):
    resp = await user_client.get("/api/v1/feeds")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["page"] == 1
    assert len(data["items"]) == 3
    assert all(not item["is_subscribed"] for item in data["items"])


async def test_list_feeds_pagination(user_client, sample_feeds):
    resp = await user_client.get("/api/v1/feeds?page=1&size=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["pages"] == 2
    assert len(data["items"]) == 2


async def test_filter_by_category(user_client, feeds_by_category, category):
    resp = await user_client.get(f"/api/v1/feeds?category_id={category.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Cat1 Feed"


# ---------------------------------------------------------------------------
# Create feed
# ---------------------------------------------------------------------------


async def test_create_feed_as_admin(admin_client):
    resp = await admin_client.post(
        "/api/v1/feeds",
        json={"url": "https://new-feed.example.com/rss.xml"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["url"] == "https://new-feed.example.com/rss.xml"
    assert data["is_subscribed"] is False
    assert data["subscriber_count"] == 0


async def test_create_feed_duplicate_url(admin_client, sample_feed):
    resp = await admin_client.post(
        "/api/v1/feeds",
        json={"url": sample_feed.url},
    )
    assert resp.status_code == 409


async def test_create_feed_as_user_allowed(user_client):
    resp = await user_client.post(
        "/api/v1/feeds",
        json={"url": "https://user-created.example.com/rss.xml"},
    )
    assert resp.status_code == 201
    assert resp.json()["url"] == "https://user-created.example.com/rss.xml"


# ---------------------------------------------------------------------------
# Get / Update / Delete feed
# ---------------------------------------------------------------------------


async def test_get_feed(user_client, sample_feed):
    resp = await user_client.get(f"/api/v1/feeds/{sample_feed.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(sample_feed.id)
    assert data["is_subscribed"] is False


async def test_feed_update_as_admin(admin_client, sample_feed):
    resp = await admin_client.put(
        f"/api/v1/feeds/{sample_feed.id}",
        json={"title": "Updated Title", "fetch_interval_min": 30},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"
    assert resp.json()["fetch_interval_min"] == 30


async def test_feed_update_as_user_allowed(user_client, sample_feed):
    resp = await user_client.put(
        f"/api/v1/feeds/{sample_feed.id}",
        json={"title": "User Updated"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "User Updated"


async def test_delete_feed_as_admin(admin_client, sample_feed):
    resp = await admin_client.delete(f"/api/v1/feeds/{sample_feed.id}")
    assert resp.status_code == 204
    # Feed should be soft-deleted (is_active = False)
    resp2 = await admin_client.get(f"/api/v1/feeds/{sample_feed.id}")
    # feed still exists but is inactive
    assert resp2.status_code == 200
    assert resp2.json()["is_active"] is False


# ---------------------------------------------------------------------------
# Subscribe / Unsubscribe
# ---------------------------------------------------------------------------


async def test_subscribe(user_client, sample_feed):
    resp = await user_client.post(f"/api/v1/feeds/{sample_feed.id}/subscribe")
    assert resp.status_code == 201


async def test_subscribe_twice_conflict(user_client, subscribed_feed):
    resp = await user_client.post(f"/api/v1/feeds/{subscribed_feed.id}/subscribe")
    assert resp.status_code == 409


async def test_unsubscribe(user_client, subscribed_feed):
    resp = await user_client.delete(f"/api/v1/feeds/{subscribed_feed.id}/subscribe")
    assert resp.status_code == 204


async def test_unsubscribe_not_subscribed(user_client, sample_feed):
    resp = await user_client.delete(f"/api/v1/feeds/{sample_feed.id}/subscribe")
    assert resp.status_code == 404


async def test_subscribed_feeds_list(user_client, subscribed_feeds):
    resp = await user_client.get("/api/v1/feeds/subscribed")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert all(item["is_subscribed"] for item in data)


async def test_is_subscribed_field(user_client, subscribed_feed):
    resp = await user_client.get(f"/api/v1/feeds/{subscribed_feed.id}")
    assert resp.status_code == 200
    assert resp.json()["is_subscribed"] is True


async def test_subscriber_count(user_client, sample_feed, db_session, admin_user, regular_user):
    # Insert two subscriptions directly to avoid single-client login conflict
    uf1 = UserFeed(user_id=admin_user.id, feed_id=sample_feed.id)
    uf2 = UserFeed(user_id=regular_user.id, feed_id=sample_feed.id)
    db_session.add(uf1)
    db_session.add(uf2)
    await db_session.commit()
    resp = await user_client.get(f"/api/v1/feeds/{sample_feed.id}")
    assert resp.status_code == 200
    assert resp.json()["subscriber_count"] == 2
    assert resp.json()["is_subscribed"] is True


async def test_subscribed_only_filter(user_client, subscribed_feed, sample_feeds):
    """?subscribed=true returns only subscribed feeds."""
    resp = await user_client.get("/api/v1/feeds?subscribed=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == str(subscribed_feed.id)


# ---------------------------------------------------------------------------
# Refresh (stub)
# ---------------------------------------------------------------------------


async def test_refresh_returns_202(admin_client, sample_feed):
    resp = await admin_client.post(f"/api/v1/feeds/{sample_feed.id}/refresh")
    assert resp.status_code == 202


async def test_create_feed_ssrf_localhost_blocked(admin_client):
    resp = await admin_client.post("/api/v1/feeds", json={"url": "http://localhost/evil"})
    assert resp.status_code == 422


async def test_create_feed_ssrf_private_ip_blocked(admin_client):
    resp = await admin_client.post("/api/v1/feeds", json={"url": "http://192.168.1.1/feed"})
    assert resp.status_code == 422


async def test_create_feed_ssrf_loopback_ip_blocked(admin_client):
    resp = await admin_client.post("/api/v1/feeds", json={"url": "http://127.0.0.1/feed"})
    assert resp.status_code == 422


async def test_create_feed_ssrf_ftp_blocked(admin_client):
    resp = await admin_client.post("/api/v1/feeds", json={"url": "ftp://example.com/feed"})
    assert resp.status_code == 422


def test_validate_feed_url_allows_public_domains():
    from app.services.feed_service import validate_feed_url
    # Should not raise
    validate_feed_url("https://feeds.bbci.co.uk/news/rss.xml")
    validate_feed_url("http://rss.example.com/feed.atom")


# ---------------------------------------------------------------------------
# fulltext_include_images
# ---------------------------------------------------------------------------


async def test_create_feed_with_fulltext_include_images(admin_client):
    resp = await admin_client.post(
        "/api/v1/feeds",
        json={
            "url": "https://comics.example.com/feed.xml",
            "fulltext_enabled": True,
            "fulltext_include_images": True,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["fulltext_enabled"] is True
    assert data["fulltext_include_images"] is True


async def test_update_feed_fulltext_include_images(admin_client, sample_feed):
    resp = await admin_client.put(
        f"/api/v1/feeds/{sample_feed.id}",
        json={"fulltext_enabled": True, "fulltext_include_images": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["fulltext_include_images"] is True


async def test_fulltext_include_images_default_false(admin_client):
    resp = await admin_client.post(
        "/api/v1/feeds",
        json={"url": "https://noimg.example.com/feed.xml"},
    )
    assert resp.status_code == 201
    assert resp.json()["fulltext_include_images"] is False


# ---------------------------------------------------------------------------
# BLOCKED → PENDING reset on re-enable
# ---------------------------------------------------------------------------


async def test_reenable_fulltext_resets_blocked_articles(admin_client, db_session, sample_feed):
    from app.models.article import Article, FulltextStatus
    from uuid import uuid4

    # Disable fulltext and create a blocked article
    sample_feed.fulltext_enabled = False
    await db_session.commit()

    blocked = Article(
        feed_id=sample_feed.id,
        guid=str(uuid4()),
        url="https://example.com/blocked",
        fulltext_status=FulltextStatus.BLOCKED.value,
        tags=[],
        tags_source="none",
    )
    db_session.add(blocked)
    await db_session.commit()
    await db_session.refresh(blocked)

    # Re-enable fulltext via API
    resp = await admin_client.put(
        f"/api/v1/feeds/{sample_feed.id}",
        json={"fulltext_enabled": True},
    )
    assert resp.status_code == 200

    await db_session.refresh(blocked)
    assert blocked.fulltext_status == FulltextStatus.PENDING.value


async def test_reenable_fulltext_resets_failed_articles(admin_client, db_session, sample_feed):
    """FAILED articles are also reset to PENDING when re-enabling fulltext."""
    from app.models.article import Article, FulltextStatus
    from uuid import uuid4

    sample_feed.fulltext_enabled = False
    await db_session.commit()

    failed = Article(
        feed_id=sample_feed.id,
        guid=str(uuid4()),
        url="https://example.com/failed",
        fulltext_status=FulltextStatus.FAILED.value,
        tags=[],
        tags_source="none",
    )
    db_session.add(failed)
    await db_session.commit()
    await db_session.refresh(failed)

    resp = await admin_client.put(
        f"/api/v1/feeds/{sample_feed.id}",
        json={"fulltext_enabled": True},
    )
    assert resp.status_code == 200

    await db_session.refresh(failed)
    assert failed.fulltext_status == FulltextStatus.PENDING.value


async def test_disable_fulltext_does_not_reset_pending_articles(admin_client, db_session, sample_feed):
    """Disabling fulltext leaves existing PENDING articles untouched."""
    from app.models.article import Article, FulltextStatus
    from uuid import uuid4

    sample_feed.fulltext_enabled = True
    await db_session.commit()

    pending = Article(
        feed_id=sample_feed.id,
        guid=str(uuid4()),
        url="https://example.com/pending",
        fulltext_status=FulltextStatus.PENDING.value,
        tags=[],
        tags_source="none",
    )
    db_session.add(pending)
    await db_session.commit()
    await db_session.refresh(pending)

    resp = await admin_client.put(
        f"/api/v1/feeds/{sample_feed.id}",
        json={"fulltext_enabled": False},
    )
    assert resp.status_code == 200

    await db_session.refresh(pending)
    # PENDING articles are not touched when disabling; they'll be BLOCKED on next open
    assert pending.fulltext_status == FulltextStatus.PENDING.value


async def test_resave_enabled_feed_retries_failed_articles(admin_client, db_session, sample_feed):
    """Re-saving a feed that's already enabled with fulltext_enabled=True resets FAILED articles."""
    from app.models.article import Article, FulltextStatus
    from uuid import uuid4

    sample_feed.fulltext_enabled = True
    await db_session.commit()

    failed = Article(
        feed_id=sample_feed.id,
        guid=str(uuid4()),
        url="https://example.com/failed-retry",
        fulltext_status=FulltextStatus.FAILED.value,
        tags=[],
        tags_source="none",
    )
    db_session.add(failed)
    await db_session.commit()
    await db_session.refresh(failed)

    # Re-save with fulltext still enabled — acts as a retry trigger
    resp = await admin_client.put(
        f"/api/v1/feeds/{sample_feed.id}",
        json={"fulltext_enabled": True},
    )
    assert resp.status_code == 200

    await db_session.refresh(failed)
    assert failed.fulltext_status == FulltextStatus.PENDING.value
