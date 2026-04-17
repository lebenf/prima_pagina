import pytest

from app.models.feed import Feed


# ---------------------------------------------------------------------------
# Test-local fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def feed_in_category(db_session, category):
    feed = Feed(url="https://cat-feed.com/rss.xml", title="Cat Feed", category_id=category.id)
    db_session.add(feed)
    await db_session.commit()
    await db_session.refresh(feed)
    return feed


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_list_categories_empty(client):
    """No auth required, returns empty list when no categories exist."""
    resp = await client.get("/api/v1/categories")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_categories_localized(client, category):
    resp = await client.get("/api/v1/categories?lang=en")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Technology"
    assert data[0]["slug"] == "technology"


async def test_list_categories_localized_it(client, category):
    resp = await client.get("/api/v1/categories?lang=it")
    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "Tecnologia"


async def test_list_categories_fallback_lang(client, category):
    """Unknown lang falls back to 'en' then 'it'."""
    resp = await client.get("/api/v1/categories?lang=ja")
    assert resp.status_code == 200
    # fallback to English
    assert resp.json()[0]["name"] in ("Technology", "Tecnologia")


async def test_list_categories_uses_user_lang(user_client, category):
    """When no ?lang param, uses authenticated user's preferred_lang."""
    # default preferred_lang is "it"
    resp = await user_client.get("/api/v1/categories")
    assert resp.status_code == 200
    assert resp.json()[0]["name"] == "Tecnologia"


async def test_create_category_as_admin(admin_client):
    resp = await admin_client.post(
        "/api/v1/categories",
        json={"slug": "politics", "name": {"it": "Politica", "en": "Politics"}},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["slug"] == "politics"
    assert data["name"]["en"] == "Politics"


async def test_create_category_as_user_forbidden(user_client):
    resp = await user_client.post(
        "/api/v1/categories",
        json={"slug": "forbidden", "name": {"it": "Vietato"}},
    )
    assert resp.status_code == 403


async def test_category_slug_unique(admin_client, category):
    resp = await admin_client.post(
        "/api/v1/categories",
        json={"slug": "technology", "name": {"it": "Dup"}},
    )
    assert resp.status_code == 409


async def test_update_category_as_admin(admin_client, category):
    resp = await admin_client.put(
        f"/api/v1/categories/{category.id}",
        json={"name": {"it": "Tech", "en": "Tech Updated"}},
    )
    assert resp.status_code == 200
    assert resp.json()["name"]["en"] == "Tech Updated"


async def test_update_category_as_user_forbidden(user_client, category):
    resp = await user_client.put(
        f"/api/v1/categories/{category.id}",
        json={"name": {"it": "Blocked"}},
    )
    assert resp.status_code == 403


async def test_delete_category_as_admin(admin_client, category):
    resp = await admin_client.delete(f"/api/v1/categories/{category.id}")
    assert resp.status_code == 204


async def test_delete_category_with_feeds_conflict(admin_client, feed_in_category, category):
    resp = await admin_client.delete(f"/api/v1/categories/{category.id}")
    assert resp.status_code == 409


async def test_delete_category_not_found(admin_client):
    import uuid
    resp = await admin_client.delete(f"/api/v1/categories/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_create_category_with_parent(admin_client, category):
    resp = await admin_client.post(
        "/api/v1/categories",
        json={"slug": "ai", "name": {"it": "AI", "en": "AI"}, "parent_id": str(category.id)},
    )
    assert resp.status_code == 201
    assert resp.json()["parent_id"] == str(category.id)
