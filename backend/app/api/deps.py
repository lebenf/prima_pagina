# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.session import Session
from app.models.user import User
from app.services.auth_service import get_session


async def get_current_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Session:
    raw = request.cookies.get("pp_session")
    if not raw:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        session_id = uuid.UUID(raw)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid session")
    session = await get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return session


async def get_current_user(
    session: Session = Depends(get_current_session),
) -> User:
    return session.user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    return current_user


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    raw = request.cookies.get("pp_session")
    if not raw:
        return None
    try:
        session_id = uuid.UUID(raw)
    except ValueError:
        return None
    session = await get_session(db, session_id)
    return session.user if session else None
