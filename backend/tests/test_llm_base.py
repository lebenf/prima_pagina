# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for LLMProvider._parse_json_object — the shared tolerant JSON
parser used by event clustering / event summary regeneration to survive
markdown fences and chat-style preamble some models add despite instructions."""
from app.services.llm.base import LLMProvider


def test_parse_clean_json():
    assert LLMProvider._parse_json_object('{"event_index": 1}') == {"event_index": 1}


def test_parse_json_with_fence():
    raw = '```json\n{"event_index": 2}\n```'
    assert LLMProvider._parse_json_object(raw) == {"event_index": 2}


def test_parse_json_with_bare_fence():
    raw = '```\n{"event_index": null}\n```'
    assert LLMProvider._parse_json_object(raw) == {"event_index": None}


def test_parse_json_with_leading_prose():
    raw = 'Certo, ecco la risposta:\n{"title": "T", "synopsis": "S"}'
    assert LLMProvider._parse_json_object(raw) == {"title": "T", "synopsis": "S"}


def test_parse_json_with_trailing_prose():
    raw = '{"event_index": 3} — this is my answer.'
    assert LLMProvider._parse_json_object(raw) == {"event_index": 3}


def test_parse_unparseable_returns_none():
    assert LLMProvider._parse_json_object("not valid json at all") is None


def test_parse_empty_returns_none():
    assert LLMProvider._parse_json_object("") is None
    assert LLMProvider._parse_json_object(None) is None


def test_parse_json_array_returns_none():
    # We only ever expect an object back from these prompts, never a bare array
    assert LLMProvider._parse_json_object("[1, 2, 3]") is None
