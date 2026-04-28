# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""llm_configs: add timeout_sec column

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-23

"""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "llm_configs",
        sa.Column("timeout_sec", sa.Integer(), nullable=False, server_default="300"),
    )


def downgrade() -> None:
    op.drop_column("llm_configs", "timeout_sec")
