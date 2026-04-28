# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.article_vote import ArticleVote
from app.models.user_topic_preference import UserTopicPreference
from app.schemas.vote import VoteResponse

VOTE_DELTA = 0.5
SCORE_MIN = -5.0
SCORE_MAX = +5.0


async def cast_vote(
    db: AsyncSession,
    user_id: UUID,
    article_id: UUID,
    vote: int,
) -> VoteResponse:
    """Upsert vote and update user_topic_preferences. Handles direction changes correctly."""
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Articolo non trovato")

    tags = article.tags or []
    existing = await db.get(ArticleVote, (user_id, article_id))
    old_vote = existing.vote if existing else 0

    if existing:
        existing.vote = vote
        existing.voted_at = datetime.utcnow()
    else:
        db.add(ArticleVote(user_id=user_id, article_id=article_id, vote=vote))

    delta = (vote - old_vote) * VOTE_DELTA
    await _update_topic_prefs(db, user_id, tags, delta)
    await db.commit()

    return VoteResponse(article_id=article_id, vote=vote, topic_scores_updated=tags)


async def remove_vote(
    db: AsyncSession,
    user_id: UUID,
    article_id: UUID,
) -> VoteResponse:
    """Remove vote and subtract its contribution from topic preferences."""
    existing = await db.get(ArticleVote, (user_id, article_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Nessun voto da rimuovere")

    article = await db.get(Article, article_id)
    tags = article.tags or []
    old_vote = existing.vote

    await db.delete(existing)
    await _update_topic_prefs(db, user_id, tags, -old_vote * VOTE_DELTA)
    await db.commit()

    return VoteResponse(article_id=article_id, vote=0, topic_scores_updated=tags)


async def _update_topic_prefs(
    db: AsyncSession,
    user_id: UUID,
    tags: list[str],
    delta: float,
) -> None:
    for tag in tags:
        pref = await db.get(UserTopicPreference, (user_id, tag))
        if pref:
            pref.score = max(SCORE_MIN, min(SCORE_MAX, pref.score + delta))
            pref.vote_count += 1
        else:
            db.add(UserTopicPreference(
                user_id=user_id,
                tag=tag,
                score=max(SCORE_MIN, min(SCORE_MAX, delta)),
                vote_count=1,
            ))


async def get_user_vote(db: AsyncSession, user_id: UUID, article_id: UUID) -> int:
    """Return current vote: +1, -1, or 0 (no vote)."""
    vote = await db.get(ArticleVote, (user_id, article_id))
    return vote.vote if vote else 0


async def get_topic_preferences(db: AsyncSession, user_id: UUID) -> dict[str, float]:
    """Return {tag: raw_score} for the user, used in ranking."""
    result = await db.execute(
        select(UserTopicPreference).where(UserTopicPreference.user_id == user_id)
    )
    return {p.tag: p.score for p in result.scalars()}


async def load_user_votes_bulk(
    db: AsyncSession,
    user_id: UUID,
    article_ids: list[UUID],
) -> dict[UUID, int]:
    """Single query to load all votes for a list of articles."""
    if not article_ids:
        return {}
    result = await db.execute(
        select(ArticleVote).where(
            ArticleVote.user_id == user_id,
            ArticleVote.article_id.in_(article_ids),
        )
    )
    return {v.article_id: v.vote for v in result.scalars()}
