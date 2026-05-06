"""fulltext_include_images

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-06 10:48:19.579733

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0009'
down_revision: Union[str, Sequence[str], None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('feeds') as batch_op:
        batch_op.add_column(
            sa.Column('fulltext_include_images', sa.Boolean(), nullable=False, server_default='0')
        )


def downgrade() -> None:
    with op.batch_alter_table('feeds') as batch_op:
        batch_op.drop_column('fulltext_include_images')
