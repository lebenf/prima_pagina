import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_optional_user
from app.models.digest import Digest
from app.models.user import User
from app.models.virtual_feed import VirtualFeed
from app.schemas.article import ArticleListResponse
from app.schemas.virtual_feed import (
    FilterPreviewRequest,
    TokenResponse,
    VirtualFeedCreate,
    VirtualFeedResponse,
    VirtualFeedUpdate,
)
from app.services import virtual_feed_service
from app.services.rss_generator import generate_atom_feed

router = APIRouter(tags=["virtual-feeds"])


def _rss_url(request: Request, vf: VirtualFeed) -> str:
    base = str(request.base_url)
    return f"{base}api/v1/virtual-feeds/{vf.id}/rss?token={vf.rss_token}"


async def _make_response(
    request: Request,
    vf: VirtualFeed,
    db: AsyncSession,
) -> VirtualFeedResponse:
    count = await virtual_feed_service.count_virtual_feed_articles(db, vf)
    return VirtualFeedResponse(
        id=vf.id,
        user_id=vf.user_id,
        name=vf.name,
        description=vf.description,
        filter_type=vf.filter_type,
        filter_config=vf.filter_config,
        is_shared=vf.is_shared,
        rss_token=vf.rss_token,
        include_digest=vf.include_digest,
        rss_url=_rss_url(request, vf),
        article_count=count,
        created_at=vf.created_at,
        updated_at=vf.updated_at,
    )


async def _get_owned_vf(vf_id: uuid.UUID, user: User, db: AsyncSession) -> VirtualFeed:
    vf = await db.get(VirtualFeed, vf_id)
    if not vf:
        raise HTTPException(status_code=404, detail="Virtual feed not found")
    if vf.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")
    return vf


# preview must be defined before /{id} to avoid FastAPI routing conflict
@router.post("/virtual-feeds/preview")
async def preview_filter(
    body: FilterPreviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await virtual_feed_service.validate_filter_config(db, body.filter_type, body.filter_config)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    fake_vf = VirtualFeed(
        user_id=current_user.id,
        name="preview",
        filter_type=body.filter_type,
        filter_config=body.filter_config,
        is_shared=False,
    )
    articles = await virtual_feed_service.get_virtual_feed_articles(db, fake_vf, limit=5)
    count = await virtual_feed_service.count_virtual_feed_articles(db, fake_vf)
    return {
        "count": count,
        "sample": [
            {"id": str(a.id), "title": a.title, "published_at": str(a.published_at)}
            for a in articles
        ],
    }


@router.get("/virtual-feeds", response_model=list[VirtualFeedResponse])
async def list_virtual_feeds(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(VirtualFeed).where(VirtualFeed.user_id == current_user.id)
        .order_by(VirtualFeed.created_at.desc())
    )
    vfs = result.scalars().all()
    return [await _make_response(request, vf, db) for vf in vfs]


@router.post("/virtual-feeds", response_model=VirtualFeedResponse, status_code=201)
async def create_virtual_feed(
    body: VirtualFeedCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await virtual_feed_service.validate_filter_config(db, body.filter_type, body.filter_config)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    vf = VirtualFeed(
        user_id=current_user.id,
        name=body.name,
        description=body.description,
        filter_type=body.filter_type,
        filter_config=body.filter_config,
        is_shared=body.is_shared,
        include_digest=body.include_digest,
    )
    db.add(vf)
    await db.commit()
    await db.refresh(vf)
    return await _make_response(request, vf, db)


@router.get("/virtual-feeds/{vf_id}", response_model=VirtualFeedResponse)
async def get_virtual_feed(
    vf_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    vf = await db.get(VirtualFeed, vf_id)
    if not vf:
        raise HTTPException(status_code=404, detail="Virtual feed not found")
    if not vf.is_shared:
        if not current_user or (current_user.id != vf.user_id and current_user.role != "admin"):
            raise HTTPException(status_code=403, detail="Not allowed")
    return await _make_response(request, vf, db)


@router.put("/virtual-feeds/{vf_id}", response_model=VirtualFeedResponse)
async def update_virtual_feed(
    vf_id: uuid.UUID,
    body: VirtualFeedUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vf = await _get_owned_vf(vf_id, current_user, db)

    filter_type = body.filter_type or vf.filter_type
    filter_config = body.filter_config or vf.filter_config

    if body.filter_config is not None:
        try:
            await virtual_feed_service.validate_filter_config(db, filter_type, filter_config)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(vf, field, value)

    await db.commit()
    await db.refresh(vf)
    return await _make_response(request, vf, db)


@router.delete("/virtual-feeds/{vf_id}", status_code=204)
async def delete_virtual_feed(
    vf_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vf = await _get_owned_vf(vf_id, current_user, db)
    await db.delete(vf)
    await db.commit()


@router.post("/virtual-feeds/{vf_id}/regenerate-token", response_model=TokenResponse)
async def regenerate_rss_token(
    vf_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vf = await _get_owned_vf(vf_id, current_user, db)
    vf.rss_token = uuid.uuid4()
    await db.commit()
    await db.refresh(vf)
    return TokenResponse(
        rss_token=vf.rss_token,
        rss_url=_rss_url(request, vf),
    )


@router.get("/virtual-feeds/{vf_id}/rss")
async def get_virtual_feed_rss(
    vf_id: uuid.UUID,
    request: Request,
    token: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    vf = await db.get(VirtualFeed, vf_id)
    if not vf:
        raise HTTPException(status_code=404, detail="Virtual feed not found")

    # Auth: shared = public; else require session or valid token
    if not vf.is_shared:
        authed = current_user and (
            current_user.id == vf.user_id or current_user.role == "admin"
        )
        if not authed:
            if not token or token != vf.rss_token:
                raise HTTPException(status_code=401, detail="Invalid or missing token")

    articles = await virtual_feed_service.get_virtual_feed_articles(db, vf, limit=50)

    # Latest digest (if include_digest=True)
    digest = None
    if vf.include_digest:
        result = await db.execute(
            select(Digest)
            .where(Digest.virtual_feed_id == vf.id)
            .order_by(Digest.created_at.desc())
            .limit(1)
        )
        digest = result.scalar_one_or_none()

    base_url = str(request.base_url)
    atom_xml = await generate_atom_feed(vf, articles, digest, base_url)

    return Response(
        content=atom_xml,
        media_type="application/atom+xml; charset=utf-8",
        headers={"Cache-Control": "max-age=300"},
    )


@router.get("/virtual-feeds/{vf_id}/articles", response_model=ArticleListResponse)
async def get_virtual_feed_articles_endpoint(
    vf_id: uuid.UUID,
    request: Request,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vf = await _get_owned_vf(vf_id, current_user, db)
    offset = (page - 1) * size
    articles = await virtual_feed_service.get_virtual_feed_articles(db, vf, limit=size, offset=offset)
    total = await virtual_feed_service.count_virtual_feed_articles(db, vf)
    import math
    from app.schemas.article import ArticleListItem
    items = [
        ArticleListItem(
            id=a.id,
            feed_id=a.feed_id,
            feed_title=a.feed.title if getattr(a, "feed", None) else None,
            title=a.title,
            url=a.url,
            author=a.author,
            content_excerpt=a.content_excerpt,
            language=a.language,
            tags=a.tags or [],
            published_at=a.published_at,
            fetched_at=a.fetched_at,
        )
        for a in articles
    ]
    return ArticleListResponse(
        items=items,
        total=total,
        page=page,
        pages=math.ceil(total / size) if total else 1,
        unread_count=0,
    )
