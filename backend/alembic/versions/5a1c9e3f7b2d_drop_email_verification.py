"""drop email verification

Revision ID: 5a1c9e3f7b2d
Revises: 38048aa1213a
Create Date: 2026-10-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a1c9e3f7b2d'
down_revision: Union[str, None] = '38048aa1213a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('users', 'email_verified')


def downgrade() -> None:
    op.add_column(
        'users',
        sa.Column('email_verified', sa.Boolean(), server_default=sa.false(), nullable=False),
    )
