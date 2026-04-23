# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import math
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession


def recency_score(published_at: datetime | None) -> float:
    """Exponential decay with 12-hour half-life. Returns value in (0, 1]."""
    if published_at is None:
        return 0.0
    age_hours = (datetime.utcnow() - published_at).total_seconds() / 3600
    return math.exp(-age_hours * math.log(2) / 12)


async def compute_category_affinity(
    db: AsyncSession, user_id: UUID
) -> dict[UUID, float]:
    """
    Per-category read ratio over the last 30 days, scaled to [0.5, 2.0].
    Returns an empty dict if the user has no reading history — callers should
    default to 1.0 for unknown categories.
    """
    from app.models.article import Article
    from app.models.article_user_state import ArticleUserState
    from app.models.feed import Feed

    cutoff = datetime.utcnow() - timedelta(days=30)

    result = await db.execute(
        select(Feed.category_id, func.count().label("read_count"))
        .join(Article, Article.feed_id == Feed.id)
        .join(
            ArticleUserState,
            and_(
                ArticleUserState.article_id == Article.id,
                ArticleUserState.user_id == user_id,
                ArticleUserState.is_read == True,  # noqa: E712
                ArticleUserState.read_at >= cutoff,
            ),
        )
        .where(Feed.category_id.is_not(None))
        .group_by(Feed.category_id)
    )
    rows = result.all()

    if not rows:
        return {}

    total = sum(r.read_count for r in rows)
    if total == 0:
        return {}

    affinity: dict[UUID, float] = {}
    n_categories = len(rows)
    for row in rows:
        if row.category_id is None:
            continue
        # Normalise: equal distribution → 1.0; heavy reader → up to 2.0
        proportion = row.read_count / total
        expected = 1.0 / n_categories if n_categories else 1.0
        raw = proportion / expected  # 1.0 at equal distribution
        affinity[row.category_id] = max(0.5, min(2.0, raw))

    return affinity


def score_article(
    *,
    published_at: datetime | None,
    source_weight: float = 1.0,
    category_affinity: float = 1.0,
    is_read: bool = False,
) -> float:
    """
    score = recency × source_weight × category_affinity × read_penalty
    read_penalty is 0.1 for already-read articles.
    """
    read_penalty = 0.1 if is_read else 1.0
    return recency_score(published_at) * source_weight * category_affinity * read_penalty
