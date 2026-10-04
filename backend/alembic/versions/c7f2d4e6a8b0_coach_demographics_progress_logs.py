"""coach demographics and daily progress logs

Revision ID: c7f2d4e6a8b0
Revises: b3e8a1c5d7f9
Create Date: 2026-10-04 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c7f2d4e6a8b0'
down_revision: Union[str, None] = 'b3e8a1c5d7f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('coaches', sa.Column('gender', sa.String(length=20), nullable=True))
    op.add_column('coaches', sa.Column('date_of_birth', sa.Date(), nullable=True))

    op.create_table(
        'progress_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('customer_id', sa.UUID(), nullable=False),
        sa.Column('log_date', sa.Date(), nullable=False),
        sa.Column('workout', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('meals', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('mood', sa.Integer(), nullable=True),
        sa.Column('energy', sa.Integer(), nullable=True),
        sa.Column('soreness', sa.Integer(), nullable=True),
        sa.Column('sleep_hours', sa.Float(), nullable=True),
        sa.Column('notes', sa.String(length=500), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('customer_id', 'log_date'),
    )
    op.create_index(op.f('ix_progress_logs_customer_id'), 'progress_logs', ['customer_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_progress_logs_customer_id'), table_name='progress_logs')
    op.drop_table('progress_logs')
    op.drop_column('coaches', 'date_of_birth')
    op.drop_column('coaches', 'gender')
