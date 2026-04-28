# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
"""votes, llm_data, extraction_scripts, invitations

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-27

Shared migration for T15, T16, T20.
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- T15: article_llm_data ---
    op.create_table(
        "article_llm_data",
        sa.Column(
            "article_id",
            sa.UUID(),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("related_article_ids", sa.Text(), server_default="[]"),
        sa.Column("computed_at", sa.TIMESTAMP(), nullable=False),
    )

    # --- T15: article_votes ---
    op.create_table(
        "article_votes",
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "article_id",
            sa.UUID(),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("vote", sa.SmallInteger(), nullable=False),
        sa.Column("voted_at", sa.TIMESTAMP(), nullable=False),
    )
    op.create_index("ix_article_votes_user_id", "article_votes", ["user_id"])
    op.create_index("ix_article_votes_article_id", "article_votes", ["article_id"])

    # --- T15: user_topic_preferences ---
    op.create_table(
        "user_topic_preferences",
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("tag", sa.String(100), primary_key=True),
        sa.Column("score", sa.Float(), server_default="0.0"),
        sa.Column("vote_count", sa.Integer(), server_default="0"),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False),
    )
    op.create_index("ix_user_topic_pref_user_id", "user_topic_preferences", ["user_id"])

    # --- T15: fulltext_method column on articles ---
    op.add_column("articles", sa.Column("fulltext_method", sa.String(20), nullable=True))

    # --- T16: feed_extraction_scripts ---
    op.create_table(
        "feed_extraction_scripts",
        sa.Column(
            "feed_id",
            sa.UUID(),
            sa.ForeignKey("feeds.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("selectors", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("validated_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="1"),
        sa.Column("success_rate", sa.Float(), server_default="1.0"),
        sa.Column("consecutive_failures", sa.Integer(), server_default="0"),
        sa.Column("sample_url", sa.String(2048), nullable=True),
        sa.Column("sample_html_hash", sa.String(64), nullable=True),
    )

    # --- T16: new columns on feeds ---
    op.add_column("feeds", sa.Column("fulltext_enabled", sa.Boolean(), server_default="0"))
    op.add_column("feeds", sa.Column("fulltext_mode", sa.String(20), server_default="trafilatura"))

    # --- T20: user_invitations ---
    op.create_table(
        "user_invitations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("token", sa.UUID(), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column(
            "created_by",
            sa.UUID(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("used_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("used_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_user_invitations_token", "user_invitations", ["token"], unique=True)

    # --- T20: new columns on digests ---
    op.add_column("digests", sa.Column("status", sa.String(20), server_default="ok"))
    op.add_column("digests", sa.Column("generation_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("digests", "generation_error")
    op.drop_column("digests", "status")
    op.drop_index("ix_user_invitations_token", table_name="user_invitations")
    op.drop_table("user_invitations")
    op.drop_column("feeds", "fulltext_mode")
    op.drop_column("feeds", "fulltext_enabled")
    op.drop_table("feed_extraction_scripts")
    op.drop_column("articles", "fulltext_method")
    op.drop_index("ix_user_topic_pref_user_id", table_name="user_topic_preferences")
    op.drop_table("user_topic_preferences")
    op.drop_index("ix_article_votes_article_id", table_name="article_votes")
    op.drop_index("ix_article_votes_user_id", table_name="article_votes")
    op.drop_table("article_votes")
    op.drop_table("article_llm_data")
