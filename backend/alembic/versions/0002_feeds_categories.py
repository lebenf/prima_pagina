"""feeds, categories, user_feeds tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-16

"""
import json
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# Fixed UUIDs for seed categories (reproducible across runs)
_CATEGORY_SEEDS = [
    ("3b241101-e2bb-4255-8caf-4136c566a962", "world",      {"it": "Mondo",       "en": "World",      "fr": "Monde",      "de": "Welt",         "es": "Mundo",     "pt": "Mundo"}),
    ("a3f5e8d2-b3c4-4d5e-8f6a-7b8c9d0e1f2a", "politics",  {"it": "Politica",    "en": "Politics",   "fr": "Politique",  "de": "Politik",      "es": "Política",  "pt": "Política"}),
    ("c4d5e6f7-a8b9-4c0d-8e1f-2a3b4c5d6e7f", "economy",   {"it": "Economia",    "en": "Economy",    "fr": "Économie",   "de": "Wirtschaft",   "es": "Economía",  "pt": "Economia"}),
    ("d5e6f7a8-b9c0-4d1e-8f2a-3b4c5d6e7f8a", "technology",{"it": "Tecnologia",  "en": "Technology", "fr": "Technologie","de": "Technologie",  "es": "Tecnología","pt": "Tecnologia"}),
    ("e6f7a8b9-c0d1-4e2f-8a3b-4c5d6e7f8a9b", "science",   {"it": "Scienza",     "en": "Science",    "fr": "Science",    "de": "Wissenschaft", "es": "Ciencia",   "pt": "Ciência"}),
    ("f7a8b9c0-d1e2-4f3a-8b4c-5d6e7f8a9b0c", "culture",   {"it": "Cultura",     "en": "Culture",    "fr": "Culture",    "de": "Kultur",       "es": "Cultura",   "pt": "Cultura"}),
    ("a8b9c0d1-e2f3-4a4b-8c5d-6e7f8a9b0c1d", "sport",     {"it": "Sport",       "en": "Sport",      "fr": "Sport",      "de": "Sport",        "es": "Deporte",   "pt": "Esporte"}),
    ("b9c0d1e2-f3a4-4b5c-8d6e-7f8a9b0c1d2e", "local",     {"it": "Locale",      "en": "Local",      "fr": "Local",      "de": "Lokal",        "es": "Local",     "pt": "Local"}),
]


def upgrade() -> None:
    categories = op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.JSON(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "feeds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("site_url", sa.String(2048), nullable=True),
        sa.Column("favicon_url", sa.String(2048), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("fetch_interval_min", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("last_fetched_at", sa.DateTime(), nullable=True),
        sa.Column("last_etag", sa.String(500), nullable=True),
        sa.Column("last_modified", sa.String(100), nullable=True),
        sa.Column("last_status", sa.SmallInteger(), nullable=True),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("is_global", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("source_weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_index("ix_feeds_category_id", "feeds", ["category_id"])
    op.create_index("ix_feeds_is_active", "feeds", ["is_active"])

    op.create_table(
        "user_feeds",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("feed_id", sa.Uuid(), nullable=False),
        sa.Column("custom_name", sa.String(200), nullable=True),
        sa.Column("notify_on_new", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("subscribed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["feed_id"], ["feeds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "feed_id"),
    )
    op.create_index("ix_user_feeds_user_id", "user_feeds", ["user_id"])
    op.create_index("ix_user_feeds_feed_id", "user_feeds", ["feed_id"])

    # Seed categories
    from datetime import datetime
    now = datetime.utcnow()
    op.bulk_insert(
        categories,
        [
            {
                "id": uuid.UUID(seed_id),
                "slug": slug,
                "name": json.dumps(name),
                "parent_id": None,
                "created_at": now,
            }
            for seed_id, slug, name in _CATEGORY_SEEDS
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_user_feeds_feed_id", table_name="user_feeds")
    op.drop_index("ix_user_feeds_user_id", table_name="user_feeds")
    op.drop_table("user_feeds")
    op.drop_index("ix_feeds_is_active", table_name="feeds")
    op.drop_index("ix_feeds_category_id", table_name="feeds")
    op.drop_table("feeds")
    op.drop_table("categories")
