# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timedelta

import pytest


@pytest.fixture
async def invitation(db_session, admin_user):
    from app.models.user_invitation import UserInvitation
    inv = UserInvitation(
        created_by=admin_user.id,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db_session.add(inv)
    await db_session.commit()
    await db_session.refresh(inv)
    return inv


@pytest.fixture
async def expired_invitation(db_session, admin_user):
    from app.models.user_invitation import UserInvitation
    inv = UserInvitation(
        created_by=admin_user.id,
        expires_at=datetime.utcnow() - timedelta(seconds=1),
    )
    db_session.add(inv)
    await db_session.commit()
    await db_session.refresh(inv)
    return inv


@pytest.fixture
async def used_invitation(db_session, admin_user, regular_user):
    from app.models.user_invitation import UserInvitation
    inv = UserInvitation(
        created_by=admin_user.id,
        expires_at=datetime.utcnow() + timedelta(days=7),
        used_at=datetime.utcnow(),
        used_by=regular_user.id,
    )
    db_session.add(inv)
    await db_session.commit()
    await db_session.refresh(inv)
    return inv


async def test_create_invitation(admin_client):
    resp = await admin_client.post("/api/v1/admin/invitations", json={})
    assert resp.status_code == 201
    data = resp.json()
    assert "token" in data
    assert data["is_valid"] is True
    assert "invite_url" in data
    assert data["email"] is None


async def test_create_invitation_with_email(admin_client):
    resp = await admin_client.post(
        "/api/v1/admin/invitations",
        json={"email": "new@example.com", "expires_days": 3},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert data["is_valid"] is True


async def test_validate_invitation_token(client, invitation):
    resp = await client.get(f"/api/v1/auth/invitation/{invitation.token}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["email"] is None


async def test_validate_expired_token(client, expired_invitation):
    resp = await client.get(f"/api/v1/auth/invitation/{expired_invitation.token}")
    assert resp.status_code == 200
    assert resp.json()["valid"] is False


async def test_validate_used_token(client, used_invitation):
    resp = await client.get(f"/api/v1/auth/invitation/{used_invitation.token}")
    assert resp.status_code == 200
    assert resp.json()["valid"] is False


async def test_validate_nonexistent_token(client):
    import uuid
    resp = await client.get(f"/api/v1/auth/invitation/{uuid.uuid4()}")
    assert resp.status_code == 200
    assert resp.json()["valid"] is False


async def test_validate_invalid_uuid(client):
    resp = await client.get("/api/v1/auth/invitation/not-a-uuid")
    assert resp.status_code == 200
    assert resp.json()["valid"] is False


async def test_register_with_invitation(client, invitation):
    resp = await client.post(
        f"/api/v1/auth/register/{invitation.token}",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "securepass123",
            "confirm_password": "securepass123",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newuser"
    assert data["role"] == "user"


async def test_register_passwords_mismatch(client, invitation):
    resp = await client.post(
        f"/api/v1/auth/register/{invitation.token}",
        json={
            "username": "newuser2",
            "email": "newuser2@example.com",
            "password": "securepass123",
            "confirm_password": "differentpass",
        },
    )
    assert resp.status_code == 422


async def test_register_token_already_used(client, invitation):
    payload = {
        "username": "firstuser",
        "email": "firstuser@example.com",
        "password": "securepass123",
        "confirm_password": "securepass123",
    }
    r1 = await client.post(f"/api/v1/auth/register/{invitation.token}", json=payload)
    assert r1.status_code == 201

    payload2 = {
        "username": "seconduser",
        "email": "seconduser@example.com",
        "password": "securepass123",
        "confirm_password": "securepass123",
    }
    r2 = await client.post(f"/api/v1/auth/register/{invitation.token}", json=payload2)
    assert r2.status_code == 400


async def test_register_expired_invitation(client, expired_invitation):
    resp = await client.post(
        f"/api/v1/auth/register/{expired_invitation.token}",
        json={
            "username": "lateuser",
            "email": "lateuser@example.com",
            "password": "securepass123",
            "confirm_password": "securepass123",
        },
    )
    assert resp.status_code == 400


async def test_revoke_invitation(admin_client, invitation):
    resp = await admin_client.delete(f"/api/v1/admin/invitations/{invitation.id}")
    assert resp.status_code == 204

    check = await admin_client.get(f"/api/v1/auth/invitation/{invitation.token}")
    assert check.json()["valid"] is False


async def test_list_invitations(admin_client, invitation):
    resp = await admin_client.get("/api/v1/admin/invitations")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(str(i["id"]) == str(invitation.id) for i in data)


async def test_register_autologin(client, invitation):
    resp = await client.post(
        f"/api/v1/auth/register/{invitation.token}",
        json={
            "username": "autouser",
            "email": "autouser@example.com",
            "password": "securepass123",
            "confirm_password": "securepass123",
        },
    )
    assert resp.status_code == 201
    # session cookie should be set
    assert "pp_session" in resp.cookies
