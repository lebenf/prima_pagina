# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for event scoring functions in app/services/ranking.py."""
from datetime import datetime, timedelta

from app.services.ranking import event_read_penalty, event_score, source_diversity_weight


def test_read_penalty_all_read():
    assert event_read_penalty([True, True, True]) == 0.1


def test_read_penalty_none_read():
    assert event_read_penalty([False, False]) == 1.0


def test_read_penalty_partial_read():
    assert event_read_penalty([True, False, False]) == 0.4


def test_read_penalty_empty_defaults_unread():
    assert event_read_penalty([]) == 1.0


def test_source_diversity_increases_with_more_sources():
    w1 = source_diversity_weight(1)
    w3 = source_diversity_weight(3)
    w10 = source_diversity_weight(10)
    assert w1 < w3 < w10


def test_source_diversity_capped_at_2x():
    assert source_diversity_weight(100) == 2.0


def test_source_diversity_single_source_is_baseline():
    assert source_diversity_weight(1) == 1.0


def test_event_score_uses_last_activity_at_for_recency():
    recent = datetime.utcnow() - timedelta(hours=1)
    stale = datetime.utcnow() - timedelta(hours=48)
    s_recent = event_score(last_activity_at=recent, source_count=1)
    s_stale = event_score(last_activity_at=stale, source_count=1)
    assert s_recent > s_stale


def test_event_score_source_count_1_vs_3_vs_10():
    """More sources → higher score at parity of other factors, with damped growth."""
    now = datetime.utcnow()
    s1 = event_score(last_activity_at=now, source_count=1)
    s3 = event_score(last_activity_at=now, source_count=3)
    s10 = event_score(last_activity_at=now, source_count=10)
    assert s1 < s3 < s10
    # Growth is damped: the jump from 3->10 sources is proportionally smaller
    # than a naive linear scaling would produce.
    assert (s10 / s3) < (10 / 3)


def test_event_score_all_read_scores_lower_than_unread():
    now = datetime.utcnow()
    s_unread = event_score(last_activity_at=now, source_count=2, read_states=[False, False])
    s_read = event_score(last_activity_at=now, source_count=2, read_states=[True, True])
    assert s_read < s_unread
