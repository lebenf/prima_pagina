from datetime import datetime, timedelta

import pytest

from app.models.session import Session
from tests.conftest import ADMIN_PASSWORD, USER_PASSWORD


# ---------------------------------------------------------------------------
# Test-local fixtures (not shared with other test modules)
# ---------------------------------------------------------------------------


@pytest.fixture
async def admin_session_obj(db_session, admin_user):
    """A valid Session row for admin (created directly in DB)."""
    s = Session(
        user_id=admin_user.id,
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s


@pytest.fixture
async def expired_session(db_session, admin_user):
    s = Session(
        user_id=admin_user.id,
        expires_at=datetime.utcnow() - timedelta(seconds=1),
    )
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s


@pytest.fixture
async def revoked_session(db_session, admin_user):
    s = Session(
        user_id=admin_user.id,
        expires_at=datetime.utcnow() + timedelta(days=30),
        is_revoked=True,
    )
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


async def test_login_success(client, admin_user):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == admin_user.username
    assert data["role"] == "admin"
    assert "pp_session" in resp.cookies


async def test_login_wrong_password(client, admin_user):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "wrong"},
    )
    assert resp.status_code == 401


async def test_login_wrong_username(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "irrelevant"},
    )
    assert resp.status_code == 401


async def test_login_by_email(client, admin_user):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.email, "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------


async def test_me_authenticated(admin_client):
    resp = await admin_client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


async def test_me_unauthenticated(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


async def test_logout(admin_client):
    resp = await admin_client.post("/api/v1/auth/logout")
    assert resp.status_code == 204
    resp2 = await admin_client.get("/api/v1/auth/me")
    assert resp2.status_code == 401


# ---------------------------------------------------------------------------
# Session validity
# ---------------------------------------------------------------------------


async def test_session_expired(client, expired_session):
    client.cookies.set("pp_session", str(expired_session.id))
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_session_revoked(client, revoked_session):
    client.cookies.set("pp_session", str(revoked_session.id))
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Admin protection
# ---------------------------------------------------------------------------


async def test_admin_required_as_user(user_client):
    resp = await user_client.post(
        "/api/v1/auth/users",
        json={"email": "new@test.com", "username": "newuser", "password": "password123"},
    )
    assert resp.status_code == 403


async def test_admin_required_as_admin(admin_client):
    resp = await admin_client.post(
        "/api/v1/auth/users",
        json={"email": "new@test.com", "username": "newuser", "password": "password123"},
    )
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Session list and revocation
# ---------------------------------------------------------------------------


async def test_list_sessions(admin_client):
    resp = await admin_client.get("/api/v1/auth/sessions")
    assert resp.status_code == 200
    sessions = resp.json()
    assert len(sessions) >= 1
    current = [s for s in sessions if s["is_current"]]
    assert len(current) == 1


async def test_revoke_own_session(admin_client):
    sessions_resp = await admin_client.get("/api/v1/auth/sessions")
    current = next(s for s in sessions_resp.json() if s["is_current"])
    resp = await admin_client.delete(f"/api/v1/auth/sessions/{current['id']}")
    assert resp.status_code == 204


async def test_revoke_other_session_forbidden(user_client, admin_session_obj):
    resp = await user_client.delete(f"/api/v1/auth/sessions/{admin_session_obj.id}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


async def test_login_rate_limit(client, admin_user):
    for i in range(5):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"username": admin_user.username, "password": "wrong"},
        )
        assert resp.status_code == 401, f"Expected 401 on attempt {i + 1}"
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": admin_user.username, "password": "wrong"},
    )
    assert resp.status_code == 429


# ---------------------------------------------------------------------------
# cleanup_expired_sessions
# ---------------------------------------------------------------------------


async def test_cleanup_expired(db_session, admin_user):
    from app.services.auth_service import cleanup_expired_sessions

    for _ in range(3):
        s = Session(user_id=admin_user.id, expires_at=datetime.utcnow() - timedelta(days=1))
        db_session.add(s)
    valid = Session(user_id=admin_user.id, expires_at=datetime.utcnow() + timedelta(days=30))
    db_session.add(valid)
    await db_session.commit()

    count = await cleanup_expired_sessions(db_session)
    assert count == 3


# ---------------------------------------------------------------------------
# create_initial_admin
# ---------------------------------------------------------------------------


async def test_create_initial_admin_skips_if_exists(db_session, admin_user):
    from app.services.auth_service import create_initial_admin

    from app.config import get_settings
    settings = get_settings()
    settings_with_admin = type(settings)(
        **{**settings.model_dump(), "admin_email": "neo@test.com", "admin_username": "neo", "admin_password": "SomePass123!"}
    )
    import app.services.auth_service as svc
    original = svc.get_settings
    svc.get_settings = lambda: settings_with_admin
    try:
        result = await create_initial_admin(db_session)
    finally:
        svc.get_settings = original
    assert result is None


# ---------------------------------------------------------------------------
# User creation & profile
# ---------------------------------------------------------------------------


async def test_create_user_as_admin(admin_client):
    resp = await admin_client.post(
        "/api/v1/auth/users",
        json={"email": "created@test.com", "username": "createduser", "password": "password123", "role": "user"},
    )
    assert resp.status_code == 201
    assert resp.json()["username"] == "createduser"


async def test_create_user_as_user_forbidden(user_client):
    resp = await user_client.post(
        "/api/v1/auth/users",
        json={"email": "blocked@test.com", "username": "blocked", "password": "password123"},
    )
    assert resp.status_code == 403


async def test_change_language(user_client):
    resp = await user_client.patch("/api/v1/auth/me", json={"preferred_lang": "en"})
    assert resp.status_code == 200
    assert resp.json()["preferred_lang"] == "en"


async def test_change_password(user_client):
    resp = await user_client.patch(
        "/api/v1/auth/me",
        json={"current_password": USER_PASSWORD, "new_password": "NewPass456!"},
    )
    assert resp.status_code == 200


async def test_change_password_wrong_current(user_client):
    resp = await user_client.patch(
        "/api/v1/auth/me",
        json={"current_password": "wrongcurrent", "new_password": "NewPass456!"},
    )
    assert resp.status_code == 400
