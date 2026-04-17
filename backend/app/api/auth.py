from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_session, get_current_user, require_admin
from app.config import get_settings
from app.database import get_db
from app.limiter import limiter
from app.models.session import Session
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    SessionResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services.auth_service import (
    authenticate_user,
    create_session,
    hash_password,
    revoke_session,
    verify_password,
)

router = APIRouter(tags=["auth"])
settings = get_settings()


@router.post("/auth/login", response_model=UserResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_user(db, body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    session = await create_session(db, user, request)
    response.set_cookie(
        key="pp_session",
        value=str(session.id),
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookies,
        max_age=settings.session_max_age_days * 86400,
    )
    return user


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    await revoke_session(db, session.id)
    response.delete_cookie("pp_session")


@router.get("/auth/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/auth/sessions", response_model=list[SessionResponse])
async def list_sessions(
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Session).where(Session.user_id == session.user_id)
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return [
        SessionResponse(
            id=s.id,
            created_at=s.created_at,
            expires_at=s.expires_at,
            last_active_at=s.last_active_at,
            ip_address=s.ip_address,
            user_agent=s.user_agent,
            is_revoked=s.is_revoked,
            is_current=(s.id == session.id),
        )
        for s in sessions
    ]


@router.delete("/auth/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_user_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid as _uuid
    try:
        sid = _uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")

    ok = await revoke_session(db, sid, user_id=current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")


@router.patch("/auth/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.preferred_lang is not None:
        current_user.preferred_lang = body.preferred_lang

    if body.new_password is not None:
        if not body.current_password:
            raise HTTPException(status_code=400, detail="current_password required to change password")
        if not verify_password(body.current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        current_user.hashed_password = hash_password(body.new_password)

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/auth/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Check uniqueness
    result = await db.execute(
        select(User).where((User.email == body.email) | (User.username == body.username))
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email or username already exists")

    user = User(
        email=body.email,
        username=body.username,
        hashed_password=hash_password(body.password),
        role=body.role,
        preferred_lang=body.preferred_lang,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
