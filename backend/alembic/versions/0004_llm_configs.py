"""llm_configs table

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-21

"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("endpoint_url", sa.String(2048), nullable=True),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("use_for", sa.JSON(), nullable=False, server_default='["tagging","digest"]'),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_configs_is_active", "llm_configs", ["is_active"])
    op.create_index("ix_llm_configs_provider", "llm_configs", ["provider"])


def downgrade() -> None:
    op.drop_index("ix_llm_configs_provider", table_name="llm_configs")
    op.drop_index("ix_llm_configs_is_active", table_name="llm_configs")
    op.drop_table("llm_configs")
