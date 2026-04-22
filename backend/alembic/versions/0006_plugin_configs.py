"""plugin_configs table

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-22
"""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plugin_configs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("plugin_type", sa.String(50), nullable=False),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("config_json_encrypted", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_plugin_configs_user_id", "plugin_configs", ["user_id"])
    op.create_index("ix_plugin_configs_plugin_type", "plugin_configs", ["plugin_type"])
    op.create_index("ix_plugin_configs_is_active", "plugin_configs", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_plugin_configs_is_active")
    op.drop_index("ix_plugin_configs_plugin_type")
    op.drop_index("ix_plugin_configs_user_id")
    op.drop_table("plugin_configs")
