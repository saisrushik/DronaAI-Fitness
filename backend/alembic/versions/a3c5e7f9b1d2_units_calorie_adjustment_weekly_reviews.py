"""unit preference, coach calorie adjustment and weekly reviews

Revision ID: a3c5e7f9b1d2
Revises: f2a4c6e8b0d1
Create Date: 2026-11-15 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a3c5e7f9b1d2'
down_revision: Union[str, None] = 'f2a4c6e8b0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('unit_system', sa.String(length=10), server_default='metric', nullable=False))
    op.add_column('customers', sa.Column('calorie_adjustment', sa.Integer(), server_default='0', nullable=False))

    op.create_table(
        'weekly_reviews',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('customer_id', sa.UUID(), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('stats', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('summary', sa.String(length=1000), nullable=False),
        sa.Column('recommended_adjustment', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=12), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('customer_id', 'period_end'),
    )
    op.create_index(op.f('ix_weekly_reviews_customer_id'), 'weekly_reviews', ['customer_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_weekly_reviews_customer_id'), table_name='weekly_reviews')
    op.drop_table('weekly_reviews')
    op.drop_column('customers', 'calorie_adjustment')
    op.drop_column('users', 'unit_system')
