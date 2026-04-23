# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — registers all models with Base.metadata
from app.config import Settings, get_settings
from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


def get_test_settings() -> Settings:
    return Settings(
        secret_key="test-secret-key-not-for-production",
        encryption_key="dGVzdC1lbmNyeXB0aW9uLWtleS0zMmJ5dGVzISEhISE=",
        database_url=TEST_DATABASE_URL,
        app_env="development",
    )


@pytest.fixture(scope="session")
def test_settings():
    return get_test_settings()


@pytest.fixture(autouse=True)
def override_settings(test_settings):
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield
    app.dependency_overrides.pop(get_settings, None)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    yield
    from app.limiter import limiter
    limiter._storage.reset()


@pytest.fixture
async def db_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(db_engine):
    session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# User helpers (shared with test_auth.py)
# ---------------------------------------------------------------------------

ADMIN_PASSWORD = "AdminPass123!"
USER_PASSWORD = "UserPass123!"


@pytest.fixture
async def admin_user(db_session):
    from app.models.user import User
    from app.services.auth_service import hash_password
    user = User(email="admin@test.com", username="admin", hashed_password=hash_password(ADMIN_PASSWORD), role="admin")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def regular_user(db_session):
    from app.models.user import User
    from app.services.auth_service import hash_password
    user = User(email="user@test.com", username="regular", hashed_password=hash_password(USER_PASSWORD), role="user")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_client(client, admin_user):
    resp = await client.post("/api/v1/auth/login", json={"username": admin_user.username, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200
    return client


@pytest.fixture
async def user_client(client, regular_user):
    resp = await client.post("/api/v1/auth/login", json={"username": regular_user.username, "password": USER_PASSWORD})
    assert resp.status_code == 200
    return client


# ---------------------------------------------------------------------------
# Category / Feed helpers
# ---------------------------------------------------------------------------


@pytest.fixture
async def category(db_session):
    from app.models.category import Category
    cat = Category(slug="technology", name={"it": "Tecnologia", "en": "Technology", "fr": "Technologie"})
    db_session.add(cat)
    await db_session.commit()
    await db_session.refresh(cat)
    return cat


@pytest.fixture
async def another_category(db_session):
    from app.models.category import Category
    cat = Category(slug="science", name={"it": "Scienza", "en": "Science"})
    db_session.add(cat)
    await db_session.commit()
    await db_session.refresh(cat)
    return cat


@pytest.fixture
async def sample_feed(db_session):
    from app.models.feed import Feed
    feed = Feed(url="https://example.com/feed.xml", title="Example Feed")
    db_session.add(feed)
    await db_session.commit()
    await db_session.refresh(feed)
    return feed
