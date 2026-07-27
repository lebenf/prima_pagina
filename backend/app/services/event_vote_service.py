# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Event voting — mirrors vote_service.py's article-vote logic, but updates
topic preferences from the event's own (already-unioned) tags rather than
re-deriving the union from member articles each time."""
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.event_vote import EventVote
from app.schemas.event import EventVoteResponse
from app.services.topic_preference_service import apply_topic_preference_delta

VOTE_DELTA = 0.5


async def cast_vote(
    db: AsyncSession,
    user_id: UUID,
    event_id: UUID,
    vote: int,
) -> EventVoteResponse:
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Evento non trovato")

    tags = event.tags or []
    existing = await db.get(EventVote, (user_id, event_id))
    old_vote = existing.vote if existing else 0

    if existing:
        existing.vote = vote
        existing.voted_at = datetime.utcnow()
    else:
        db.add(EventVote(user_id=user_id, event_id=event_id, vote=vote))

    delta = (vote - old_vote) * VOTE_DELTA
    await apply_topic_preference_delta(db, user_id, tags, delta)
    await db.commit()

    return EventVoteResponse(event_id=event_id, vote=vote, topic_scores_updated=tags)


async def remove_vote(
    db: AsyncSession,
    user_id: UUID,
    event_id: UUID,
) -> EventVoteResponse:
    existing = await db.get(EventVote, (user_id, event_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Nessun voto da rimuovere")

    event = await db.get(Event, event_id)
    tags = event.tags if event else []
    old_vote = existing.vote

    await db.delete(existing)
    await apply_topic_preference_delta(db, user_id, tags, -old_vote * VOTE_DELTA)
    await db.commit()

    return EventVoteResponse(event_id=event_id, vote=0, topic_scores_updated=tags)


async def get_user_vote(db: AsyncSession, user_id: UUID, event_id: UUID) -> int:
    vote = await db.get(EventVote, (user_id, event_id))
    return vote.vote if vote else 0


async def load_user_event_votes_bulk(
    db: AsyncSession,
    user_id: UUID,
    event_ids: list[UUID],
) -> dict[UUID, int]:
    if not event_ids:
        return {}
    result = await db.execute(
        select(EventVote).where(
            EventVote.user_id == user_id,
            EventVote.event_id.in_(event_ids),
        )
    )
    return {v.event_id: v.vote for v in result.scalars()}
