import uuid
from datetime import datetime

import pytest

from app.models.article import Article, TagsSource
from app.models.category import Category
from app.models.feed import Feed
from app.models.virtual_feed import VirtualFeed


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def category(db_session):
    cat = Category(slug="technology", name={"it": "Tecnologia", "en": "Technology"})
    db_session.add(cat)
    await db_session.commit()
    await db_session.refresh(cat)
    return cat


@pytest.fixture
async def feed_in_category(db_session, category):
    f = Feed(url="https://example.com/rss.xml", title="Tech Feed", category_id=category.id)
    db_session.add(f)
    await db_session.commit()
    await db_session.refresh(f)
    return f


@pytest.fixture
async def articles_with_tags(db_session, feed_in_category):
    arts = [
        Article(feed_id=feed_in_category.id, guid=f"g{i}", title=f"Article {i}",
                tags=["ai", "tech"] if i % 2 == 0 else ["sport"],
                tags_source=TagsSource.LLM.value,
                fetched_at=datetime.utcnow())
        for i in range(4)
    ]
    for a in arts:
        db_session.add(a)
    await db_session.commit()
    return arts


@pytest.fixture
async def virtual_feed(db_session, regular_user, feed_in_category, category):
    vf = VirtualFeed(
        user_id=regular_user.id,
        name="Tech VF",
        filter_type="category",
        filter_config={"category_id": str(category.id)},
        is_shared=False,
    )
    db_session.add(vf)
    await db_session.commit()
    await db_session.refresh(vf)
    return vf


@pytest.fixture
async def shared_virtual_feed(db_session, regular_user, category):
    vf = VirtualFeed(
        user_id=regular_user.id,
        name="Shared VF",
        filter_type="category",
        filter_config={"category_id": str(category.id)},
        is_shared=True,
    )
    db_session.add(vf)
    await db_session.commit()
    await db_session.refresh(vf)
    return vf


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------

async def test_create_virtual_feed_category(user_client, category):
    resp = await user_client.post("/api/v1/virtual-feeds", json={
        "name": "My Tech Feed",
        "filter_type": "category",
        "filter_config": {"category_id": str(category.id)},
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Tech Feed"
    assert data["filter_type"] == "category"
    assert "rss_url" in data
    assert "rss_token" in data
    assert data["article_count"] == 0


async def test_create_virtual_feed_tags_or(user_client):
    resp = await user_client.post("/api/v1/virtual-feeds", json={
        "name": "AI or Tech",
        "filter_type": "tags",
        "filter_config": {"tags": ["ai", "tech"], "operator": "OR"},
    })
    assert resp.status_code == 201


async def test_create_virtual_feed_tags_and(user_client):
    resp = await user_client.post("/api/v1/virtual-feeds", json={
        "name": "AI and Tech",
        "filter_type": "tags",
        "filter_config": {"tags": ["ai", "tech"], "operator": "AND"},
    })
    assert resp.status_code == 201


async def test_create_invalid_filter_config_missing_category_id(user_client):
    resp = await user_client.post("/api/v1/virtual-feeds", json={
        "name": "Bad",
        "filter_type": "category",
        "filter_config": {},  # missing category_id
    })
    assert resp.status_code == 422


async def test_create_invalid_filter_config_empty_tags(user_client):
    resp = await user_client.post("/api/v1/virtual-feeds", json={
        "name": "Bad",
        "filter_type": "tags",
        "filter_config": {"tags": []},  # empty tags
    })
    assert resp.status_code == 422


async def test_list_virtual_feeds(user_client, virtual_feed):
    resp = await user_client.get("/api/v1/virtual-feeds")
    assert resp.status_code == 200
    data = resp.json()
    assert any(vf["id"] == str(virtual_feed.id) for vf in data)


async def test_cannot_see_others_feed(user_client, db_session, admin_user):
    """User cannot see another user's private virtual feed."""
    other_vf = VirtualFeed(
        user_id=admin_user.id,
        name="Admin VF",
        filter_type="tags",
        filter_config={"tags": ["admin"]},
        is_shared=False,
    )
    db_session.add(other_vf)
    await db_session.commit()
    await db_session.refresh(other_vf)

    resp = await user_client.get(f"/api/v1/virtual-feeds/{other_vf.id}")
    assert resp.status_code == 403


async def test_update_virtual_feed(user_client, virtual_feed):
    resp = await user_client.put(f"/api/v1/virtual-feeds/{virtual_feed.id}", json={
        "name": "Updated Name",
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


async def test_delete_virtual_feed(user_client, virtual_feed):
    resp = await user_client.delete(f"/api/v1/virtual-feeds/{virtual_feed.id}")
    assert resp.status_code == 204

    resp2 = await user_client.get(f"/api/v1/virtual-feeds/{virtual_feed.id}")
    assert resp2.status_code in (403, 404)


async def test_regenerate_token(user_client, virtual_feed):
    old_token = str(virtual_feed.rss_token)
    resp = await user_client.post(f"/api/v1/virtual-feeds/{virtual_feed.id}/regenerate-token")
    assert resp.status_code == 200
    data = resp.json()
    assert data["rss_token"] != old_token
    assert data["rss_token"] in data["rss_url"]


# ---------------------------------------------------------------------------
# RSS endpoint tests
# ---------------------------------------------------------------------------

async def test_rss_endpoint_with_token(client, virtual_feed):
    token = str(virtual_feed.rss_token)
    resp = await client.get(f"/api/v1/virtual-feeds/{virtual_feed.id}/rss?token={token}")
    assert resp.status_code == 200
    assert "application/atom+xml" in resp.headers["content-type"]
    assert "<feed" in resp.text


async def test_rss_endpoint_wrong_token(client, virtual_feed):
    wrong = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/virtual-feeds/{virtual_feed.id}/rss?token={wrong}")
    assert resp.status_code == 401


async def test_rss_endpoint_no_token_no_auth(client, virtual_feed):
    resp = await client.get(f"/api/v1/virtual-feeds/{virtual_feed.id}/rss")
    assert resp.status_code == 401


async def test_rss_endpoint_shared_no_auth(client, shared_virtual_feed):
    resp = await client.get(f"/api/v1/virtual-feeds/{shared_virtual_feed.id}/rss")
    assert resp.status_code == 200
    assert "application/atom+xml" in resp.headers["content-type"]


async def test_rss_endpoint_authenticated_user(user_client, virtual_feed):
    resp = await user_client.get(f"/api/v1/virtual-feeds/{virtual_feed.id}/rss")
    assert resp.status_code == 200


async def test_rss_url_contains_token(user_client, virtual_feed):
    resp = await user_client.get("/api/v1/virtual-feeds")
    data = resp.json()
    vf_data = next(v for v in data if v["id"] == str(virtual_feed.id))
    assert str(virtual_feed.rss_token) in vf_data["rss_url"]


# ---------------------------------------------------------------------------
# Filter correctness tests
# ---------------------------------------------------------------------------

async def test_filter_tags_or(db_session, regular_user, articles_with_tags):
    """OR filter: articles with 'ai' OR 'tech' should match half the articles."""
    from app.services.virtual_feed_service import get_virtual_feed_articles

    vf = VirtualFeed(
        user_id=regular_user.id,
        name="OR filter",
        filter_type="tags",
        filter_config={"tags": ["ai"], "operator": "OR"},
        is_shared=False,
    )
    articles = await get_virtual_feed_articles(db_session, vf)
    # Articles 0, 2 have ['ai', 'tech']; 1, 3 have ['sport']
    assert len(articles) == 2
    for a in articles:
        assert "ai" in (a.tags or [])


async def test_filter_tags_and(db_session, regular_user, articles_with_tags):
    """AND filter: articles must have BOTH 'ai' AND 'tech'."""
    from app.services.virtual_feed_service import get_virtual_feed_articles

    vf = VirtualFeed(
        user_id=regular_user.id,
        name="AND filter",
        filter_type="tags",
        filter_config={"tags": ["ai", "tech"], "operator": "AND"},
        is_shared=False,
    )
    articles = await get_virtual_feed_articles(db_session, vf)
    assert len(articles) == 2
    for a in articles:
        assert "ai" in (a.tags or [])
        assert "tech" in (a.tags or [])


async def test_filter_category(db_session, regular_user, feed_in_category, articles_with_tags, category):
    """Category filter returns articles from feeds in the given category."""
    from app.services.virtual_feed_service import get_virtual_feed_articles, count_virtual_feed_articles

    vf = VirtualFeed(
        user_id=regular_user.id,
        name="Cat filter",
        filter_type="category",
        filter_config={"category_id": str(category.id)},
        is_shared=False,
    )
    articles = await get_virtual_feed_articles(db_session, vf)
    count = await count_virtual_feed_articles(db_session, vf)
    assert len(articles) == 4
    assert count == 4


async def test_preview_filter(user_client, articles_with_tags):
    resp = await user_client.post("/api/v1/virtual-feeds/preview", json={
        "filter_type": "tags",
        "filter_config": {"tags": ["ai"], "operator": "OR"},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data
    assert "sample" in data
    assert data["count"] >= 0


async def test_article_count_in_response(user_client, virtual_feed, articles_with_tags):
    resp = await user_client.get(f"/api/v1/virtual-feeds/{virtual_feed.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["article_count"] == 4
