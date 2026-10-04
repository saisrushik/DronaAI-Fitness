"""add diet change requests

Revision ID: 7c2e4d9a1f3b
Revises: 5a1c9e3f7b2d
Create Date: 2026-10-04 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7c2e4d9a1f3b'
down_revision: Union[str, None] = '5a1c9e3f7b2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'diet_change_requests',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('plan_id', sa.UUID(), nullable=False),
        sa.Column('customer_id', sa.UUID(), nullable=False),
        sa.Column('coach_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('requested_meals', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('approved_meals', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('note', sa.String(length=500), nullable=False),
        sa.Column('coach_note', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['plan_id'], ['workout_diet_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['coach_id'], ['coaches.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_diet_change_requests_plan_id'), 'diet_change_requests', ['plan_id'], unique=False)
    op.create_index(op.f('ix_diet_change_requests_customer_id'), 'diet_change_requests', ['customer_id'], unique=False)
    op.create_index(op.f('ix_diet_change_requests_coach_id'), 'diet_change_requests', ['coach_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_diet_change_requests_coach_id'), table_name='diet_change_requests')
    op.drop_index(op.f('ix_diet_change_requests_customer_id'), table_name='diet_change_requests')
    op.drop_index(op.f('ix_diet_change_requests_plan_id'), table_name='diet_change_requests')
    op.drop_table('diet_change_requests')
