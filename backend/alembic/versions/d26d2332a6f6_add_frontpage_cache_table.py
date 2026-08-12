"""Add frontpage_cache table for scheduled frontpage generation

Revision ID: d26d2332a6f6
Revises: 0012
Create Date: 2026-08-09 17:05:43.954577

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd26d2332a6f6'
down_revision: Union[str, Sequence[str], None] = '0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create frontpage_cache table for storing cached frontpage data
    op.create_table('frontpage_cache',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=True),
    sa.Column('data', sa.JSON(), nullable=False),
    sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('is_valid', sa.Boolean(), nullable=False),
    sa.Column('cache_type', sa.String(length=20), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('frontpage_cache', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_frontpage_cache_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('frontpage_cache', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_frontpage_cache_user_id'))

    op.drop_table('frontpage_cache')
