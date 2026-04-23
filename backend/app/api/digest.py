# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.digest import Digest
from app.models.user import User
from app.schemas.digest import DigestGenerateOptions, DigestListResponse, DigestResponse
from app.services.digest_service import DigestError, generate_digest

router = APIRouter(tags=["digests"])


async def _get_owned_digest(digest_id: uuid.UUID, user: User, db: AsyncSession) -> Digest:
    digest = await db.get(Digest, digest_id)
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    if digest.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")
    return digest


@router.get("/digests", response_model=DigestListResponse)
async def list_digests(
    virtual_feed_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base = select(Digest).where(Digest.user_id == current_user.id)
    if virtual_feed_id:
        base = base.where(Digest.virtual_feed_id == virtual_feed_id)

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar_one()

    result = await db.execute(
        base.order_by(Digest.created_at.desc())
        .limit(size)
        .offset((page - 1) * size)
    )
    items = list(result.scalars().all())

    return DigestListResponse(
        items=items,
        total=total,
        page=page,
        pages=math.ceil(total / size) if total else 1,
    )


# /latest MUST be defined before /{digest_id} to avoid routing conflict
@router.get("/digests/latest", response_model=DigestResponse)
async def get_latest_digest(
    virtual_feed_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Digest)
        .where(Digest.user_id == current_user.id)
        .order_by(Digest.created_at.desc())
        .limit(1)
    )
    if virtual_feed_id:
        stmt = stmt.where(Digest.virtual_feed_id == virtual_feed_id)

    result = await db.execute(stmt)
    digest = result.scalar_one_or_none()
    if not digest:
        raise HTTPException(status_code=404, detail="No digest found")
    return digest


@router.get("/digests/{digest_id}", response_model=DigestResponse)
async def get_digest(
    digest_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_owned_digest(digest_id, current_user, db)


@router.post("/digests/generate", response_model=DigestResponse, status_code=201)
async def generate_digest_endpoint(
    body: DigestGenerateOptions,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await generate_digest(db, current_user, body)
    except DigestError:
        raise  # handled by main.py exception handler


@router.delete("/digests/{digest_id}", status_code=204)
async def delete_digest(
    digest_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    digest = await _get_owned_digest(digest_id, current_user, db)
    await db.delete(digest)
    await db.commit()
