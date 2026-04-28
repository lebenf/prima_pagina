# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import json

from sqlalchemy import JSON, Text
from sqlalchemy.types import TypeDecorator


class SafeJSON(TypeDecorator):
    """JSON column that handles raw-string values stored outside the ORM.

    SQLite does not enforce column types, so rows inserted via plain SQL
    (e.g. during manual seeding or migration scripts) may contain a JSON
    string instead of a parsed object.  This decorator transparently
    deserialises strings on load so callers always receive a dict/list.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            return value  # already serialised
        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value  # already deserialised (e.g. PostgreSQL JSONB)
        try:
            result = json.loads(value)
            # Handle double-encoding: ORM stored a string that was already JSON
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except (TypeError, ValueError):
                    pass
            return result
        except (TypeError, ValueError):
            return value
