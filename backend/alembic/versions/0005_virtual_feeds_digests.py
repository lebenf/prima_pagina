"""virtual_feeds and digests tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-21

"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "virtual_feeds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("filter_type", sa.String(20), nullable=False),
        sa.Column("filter_config", sa.JSON(), nullable=False),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("rss_token", sa.Uuid(), nullable=False),
        sa.Column("include_digest", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rss_token", name="uq_virtual_feeds_rss_token"),
    )
    op.create_index("ix_virtual_feeds_user_id", "virtual_feeds", ["user_id"])

    op.create_table(
        "digests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("virtual_feed_id", sa.Uuid(), nullable=True),
        sa.Column("llm_provider", sa.String(50), nullable=True),
        sa.Column("llm_model", sa.String(100), nullable=True),
        sa.Column("article_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["virtual_feed_id"], ["virtual_feeds.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_digests_user_id", "digests", ["user_id"])
    op.create_index("ix_digests_virtual_feed_id", "digests", ["virtual_feed_id"])
    op.create_index("ix_digests_created_at", "digests", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_digests_created_at", table_name="digests")
    op.drop_index("ix_digests_virtual_feed_id", table_name="digests")
    op.drop_index("ix_digests_user_id", table_name="digests")
    op.drop_table("digests")
    op.drop_index("ix_virtual_feeds_user_id", table_name="virtual_feeds")
    op.drop_table("virtual_feeds")
