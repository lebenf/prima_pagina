# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class VoteRequest(BaseModel):
    vote: Literal[1, -1]


class VoteResponse(BaseModel):
    article_id: UUID
    vote: int
    topic_scores_updated: list[str]


class TopicPreferenceResponse(BaseModel):
    tag: str
    score: float
    vote_count: int
    normalized: float
