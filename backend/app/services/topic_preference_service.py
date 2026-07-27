# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared user_topic_preferences update logic, used by both article votes
(vote_service.py) and event votes (event_vote_service.py)."""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_topic_preference import UserTopicPreference

SCORE_MIN = -5.0
SCORE_MAX = +5.0


async def apply_topic_preference_delta(
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
