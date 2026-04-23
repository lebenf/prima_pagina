# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import uuid
from datetime import datetime, timedelta

import bcrypt
from fastapi import Request
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.session import Session
from app.models.user import User

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


async def authenticate_user(db: AsyncSession, username_or_email: str, password: str) -> User | None:
    stmt = select(User).where(
        or_(User.username == username_or_email, User.email == username_or_email),
        User.is_active == True,  # noqa: E712
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user


async def create_session(db: AsyncSession, user: User, request: Request) -> Session:
    settings = get_settings()
    expires_at = datetime.utcnow() + timedelta(days=settings.session_max_age_days)
    session = Session(
        user_id=user.id,
        expires_at=expires_at,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: uuid.UUID) -> Session | None:
    now = datetime.utcnow()
    stmt = (
        select(Session)
        .where(
            Session.id == session_id,
            Session.is_revoked == False,  # noqa: E712
            Session.expires_at > now,
        )
        .options(selectinload(Session.user))
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if session:
        session.last_active_at = now
        await db.commit()
    return session


async def revoke_session(db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID | None = None) -> bool:
    stmt = select(Session).where(Session.id == session_id)
    if user_id is not None:
        stmt = stmt.where(Session.user_id == user_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if session is None:
        return False
    session.is_revoked = True
    await db.commit()
    return True


async def cleanup_expired_sessions(db: AsyncSession) -> int:
    cutoff = datetime.utcnow() - timedelta(days=7)
    stmt = delete(Session).where(
        or_(
            Session.expires_at < datetime.utcnow(),
            (Session.is_revoked == True) & (Session.created_at < cutoff),  # noqa: E712
        )
    )
    result = await db.execute(stmt)
    await db.commit()
    count = result.rowcount
    logger.info("Cleaned up %d expired/revoked sessions", count)
    return count


async def create_initial_admin(db: AsyncSession) -> User | None:
    settings = get_settings()
    if not all([settings.admin_email, settings.admin_username, settings.admin_password]):
        logger.warning(
            "ADMIN_EMAIL, ADMIN_USERNAME, ADMIN_PASSWORD not set — skipping initial admin creation"
        )
        return None

    # Check if any admin already exists
    result = await db.execute(select(User).where(User.role == "admin"))
    if result.scalar_one_or_none() is not None:
        logger.info("Admin user already exists — skipping creation")
        return None

    admin = User(
        email=settings.admin_email,
        username=settings.admin_username,
        hashed_password=hash_password(settings.admin_password),
        role="admin",
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    logger.info("Initial admin user created: %s", admin.username)
    return admin
