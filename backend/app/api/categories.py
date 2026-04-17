from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_user, require_admin
from app.database import get_db
from app.models.category import Category
from app.models.feed import Feed
from app.models.user import User
from app.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategoryResponseLocalized,
    CategoryUpdate,
)

router = APIRouter(tags=["categories"])


def _localize(cat: Category, lang: str) -> CategoryResponseLocalized:
    name_dict: dict = cat.name or {}
    name = name_dict.get(lang) or name_dict.get("en") or name_dict.get("it") or next(iter(name_dict.values()), "")
    return CategoryResponseLocalized(
        id=cat.id,
        slug=cat.slug,
        name=name,
        parent_id=cat.parent_id,
        created_at=cat.created_at,
    )


@router.get("/categories", response_model=list[CategoryResponseLocalized])
async def list_categories(
    lang: str | None = Query(default=None),
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_lang = lang or (current_user.preferred_lang if current_user else "it")
    result = await db.execute(select(Category).order_by(Category.slug))
    cats = result.scalars().all()
    return [_localize(c, resolved_lang) for c in cats]


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Slug uniqueness
    existing = await db.scalar(select(Category).where(Category.slug == body.slug))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Slug already exists")

    # Validate parent
    if body.parent_id is not None:
        parent = await db.scalar(select(Category).where(Category.id == body.parent_id))
        if parent is None:
            raise HTTPException(status_code=404, detail="Parent category not found")

    cat = Category(slug=body.slug, name=body.name, parent_id=body.parent_id)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    body: CategoryUpdate,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    try:
        cid = uuid.UUID(category_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Category not found")

    cat = await db.scalar(select(Category).where(Category.id == cid))
    if cat is None:
        raise HTTPException(status_code=404, detail="Category not found")

    if body.name is not None:
        cat.name = body.name
    if body.parent_id is not None:
        if body.parent_id == cat.id:
            raise HTTPException(status_code=400, detail="Category cannot be its own parent")
        parent = await db.scalar(select(Category).where(Category.id == body.parent_id))
        if parent is None:
            raise HTTPException(status_code=404, detail="Parent category not found")
        cat.parent_id = body.parent_id

    await db.commit()
    await db.refresh(cat)
    return cat


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    try:
        cid = uuid.UUID(category_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Category not found")

    cat = await db.scalar(select(Category).where(Category.id == cid))
    if cat is None:
        raise HTTPException(status_code=404, detail="Category not found")

    # 409 if feeds are associated
    feed_count = await db.scalar(
        select(Feed).where(Feed.category_id == cid)
    )
    if feed_count is not None:
        raise HTTPException(status_code=409, detail="Cannot delete category with associated feeds")

    # 409 if child categories exist
    child_count = await db.scalar(
        select(Category).where(Category.parent_id == cid)
    )
    if child_count is not None:
        raise HTTPException(status_code=409, detail="Cannot delete category with child categories")

    await db.delete(cat)
    await db.commit()
