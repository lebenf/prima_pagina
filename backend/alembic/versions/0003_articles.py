"""articles, article_user_states tables; next_fetch_at on feeds

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-16

"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add next_fetch_at to feeds for backoff tracking
    op.add_column("feeds", sa.Column("next_fetch_at", sa.DateTime(), nullable=True))

    op.create_table(
        "articles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("feed_id", sa.Uuid(), nullable=False),
        sa.Column("guid", sa.String(2048), nullable=False),
        sa.Column("title", sa.String(1000), nullable=True),
        sa.Column("url", sa.String(2048), nullable=True),
        sa.Column("author", sa.String(500), nullable=True),
        sa.Column("content_excerpt", sa.Text(), nullable=True),
        sa.Column("content_fulltext", sa.Text(), nullable=True),
        sa.Column("fulltext_fetched_at", sa.DateTime(), nullable=True),
        sa.Column("fulltext_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("tags_source", sa.String(20), nullable=False, server_default="none"),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["feed_id"], ["feeds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feed_id", "guid", name="uq_article_feed_guid"),
    )
    op.create_index("ix_articles_feed_id", "articles", ["feed_id"])
    op.create_index("ix_articles_published_at", "articles", ["published_at"])
    op.create_index("ix_articles_tags_source", "articles", ["tags_source"])
    op.create_index("ix_articles_fulltext_status", "articles", ["fulltext_status"])

    op.create_table(
        "article_user_states",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_starred", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "article_id"),
    )
    op.create_index("ix_article_user_states_user_id", "article_user_states", ["user_id"])
    op.create_index("ix_article_user_states_article_id", "article_user_states", ["article_id"])


def downgrade() -> None:
    op.drop_index("ix_article_user_states_article_id", table_name="article_user_states")
    op.drop_index("ix_article_user_states_user_id", table_name="article_user_states")
    op.drop_table("article_user_states")
    op.drop_index("ix_articles_fulltext_status", table_name="articles")
    op.drop_index("ix_articles_tags_source", table_name="articles")
    op.drop_index("ix_articles_published_at", table_name="articles")
    op.drop_index("ix_articles_feed_id", table_name="articles")
    op.drop_table("articles")
    op.drop_column("feeds", "next_fetch_at")
