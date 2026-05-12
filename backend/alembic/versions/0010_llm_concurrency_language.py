# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""llm_configs: add max_concurrent and tagging_language columns

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-12

"""
import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "llm_configs",
        sa.Column("max_concurrent", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "llm_configs",
        sa.Column("tagging_language", sa.String(10), nullable=False, server_default="it"),
    )


def downgrade() -> None:
    op.drop_column("llm_configs", "tagging_language")
    op.drop_column("llm_configs", "max_concurrent")
