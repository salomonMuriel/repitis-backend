"""Add highest_stability and mastered_at to card_progress

Revision ID: b8c9d736e21f
Revises: a777489ed07f
Create Date: 2025-10-17 00:55:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c9d736e21f'
down_revision: Union[str, None] = 'a777489ed07f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add highest_stability column (default 0.0)
    op.add_column('card_progress', sa.Column('highest_stability', sa.Float(), nullable=False, server_default='0.0'))

    # Add mastered_at column (nullable timestamp)
    op.add_column('card_progress', sa.Column('mastered_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove the columns
    op.drop_column('card_progress', 'mastered_at')
    op.drop_column('card_progress', 'highest_stability')
