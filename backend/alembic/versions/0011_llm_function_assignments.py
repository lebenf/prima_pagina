# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""llm_function_assignments: per-function LLM provider routing

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-27

"""
import uuid
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

FUNCTIONS = ["tagging", "event_summary", "extraction_script", "related_articles", "digest"]


def upgrade() -> None:
    op.create_table(
        "llm_function_assignments",
        sa.Column("function", sa.String(30), nullable=False),
        sa.Column("primary_config_id", sa.Uuid(), sa.ForeignKey("llm_configs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("fallback_config_id", sa.Uuid(), sa.ForeignKey("llm_configs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("function"),
    )

    conn = op.get_bind()
    llm_configs = sa.table(
        "llm_configs",
        sa.column("id", sa.Uuid()),
        sa.column("provider", sa.String()),
        sa.column("use_for", sa.JSON()),
        sa.column("is_default", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
        sa.column("created_at", sa.DateTime()),
    )
    configs = conn.execute(
        sa.select(llm_configs.c.id, llm_configs.c.provider, llm_configs.c.use_for, llm_configs.c.is_default)
        .where(llm_configs.c.is_active == True)  # noqa: E712
        .order_by(llm_configs.c.is_default.desc(), llm_configs.c.created_at)
    ).fetchall()

    def _best_for(use_case: str) -> uuid.UUID | None:
        matching = [c for c in configs if use_case in (c.use_for or [])]
        if not matching:
            return None
        chosen = next((c for c in matching if c.is_default), matching[0])
        return chosen.id

    if not configs:
        import logging
        logging.getLogger(__name__).warning(
            "llm_function_assignments: no active llm_configs found — all 5 functions left unassigned, "
            "admin must configure manually"
        )

    tagging_id = _best_for("tagging")
    digest_id = _best_for("digest")

    backfill = {
        "tagging": tagging_id,
        "event_summary": None,
        "extraction_script": tagging_id,
        "related_articles": tagging_id,
        "digest": digest_id,
    }

    now = datetime.utcnow()
    assignments_table = sa.table(
        "llm_function_assignments",
        sa.column("function", sa.String()),
        sa.column("primary_config_id", sa.Uuid()),
        sa.column("fallback_config_id", sa.Uuid()),
        sa.column("updated_at", sa.DateTime()),
    )
    op.bulk_insert(
        assignments_table,
        [
            {
                "function": function,
                "primary_config_id": backfill[function],
                "fallback_config_id": None,
                "updated_at": now,
            }
            for function in FUNCTIONS
        ],
    )


def downgrade() -> None:
    op.drop_table("llm_function_assignments")
