# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""events: event aggregation, event votes, article.event_id/event_role

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-27

"""
import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("title_source", sa.String(20), nullable=False, server_default="representative"),
        sa.Column("synopsis", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("category_id", sa.Uuid(), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("article_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("opened_at", sa.DateTime(), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_status_last_activity", "events", ["status", "last_activity_at"])

    op.create_table(
        "event_votes",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("vote", sa.SmallInteger(), nullable=False),
        sa.Column("voted_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_event_votes_event_id", "event_votes", ["event_id"])

    with op.batch_alter_table("articles") as batch_op:
        batch_op.add_column(sa.Column("event_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("event_role", sa.String(20), nullable=True))
        batch_op.create_foreign_key(
            "fk_articles_event_id", "events", ["event_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.create_index("ix_articles_event_id", ["event_id"])


def downgrade() -> None:
    with op.batch_alter_table("articles") as batch_op:
        batch_op.drop_index("ix_articles_event_id")
        batch_op.drop_constraint("fk_articles_event_id", type_="foreignkey")
        batch_op.drop_column("event_role")
        batch_op.drop_column("event_id")

    op.drop_index("ix_event_votes_event_id", table_name="event_votes")
    op.drop_table("event_votes")

    op.drop_index("ix_events_status_last_activity", table_name="events")
    op.drop_table("events")
