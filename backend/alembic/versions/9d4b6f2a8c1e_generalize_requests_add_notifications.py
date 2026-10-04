"""generalize customer requests and add notifications

Revision ID: 9d4b6f2a8c1e
Revises: 7c2e4d9a1f3b
Create Date: 2026-10-04 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d4b6f2a8c1e'
down_revision: Union[str, None] = '7c2e4d9a1f3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEXED = ('plan_id', 'customer_id', 'coach_id')


def upgrade() -> None:
    op.rename_table('diet_change_requests', 'customer_requests')
    for column in _INDEXED:
        op.execute(
            f'ALTER INDEX ix_diet_change_requests_{column} RENAME TO ix_customer_requests_{column}'
        )
    # Existing rows are all meal requests.
    op.add_column(
        'customer_requests',
        sa.Column('request_type', sa.String(length=10), server_default='meal', nullable=False),
    )
    op.alter_column('customer_requests', 'request_type', server_default=None)
    op.alter_column(
        'customer_requests', 'note',
        new_column_name='description',
        type_=sa.String(length=1000),
        existing_type=sa.String(length=500),
        existing_nullable=False,
    )
    op.alter_column('customer_requests', 'plan_id', nullable=True, existing_type=sa.UUID())
    op.alter_column('customer_requests', 'requested_meals', nullable=True)

    op.create_table(
        'notifications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('request_id', sa.UUID(), nullable=True),
        sa.Column('message', sa.String(length=300), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['request_id'], ['customer_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_table('notifications')

    # Non-meal requests have no place in the old table.
    op.execute("DELETE FROM customer_requests WHERE request_type <> 'meal'")
    op.alter_column('customer_requests', 'requested_meals', nullable=False)
    op.alter_column('customer_requests', 'plan_id', nullable=False, existing_type=sa.UUID())
    op.alter_column(
        'customer_requests', 'description',
        new_column_name='note',
        type_=sa.String(length=500),
        existing_type=sa.String(length=1000),
        existing_nullable=False,
    )
    op.drop_column('customer_requests', 'request_type')
    for column in _INDEXED:
        op.execute(
            f'ALTER INDEX ix_customer_requests_{column} RENAME TO ix_diet_change_requests_{column}'
        )
    op.rename_table('customer_requests', 'diet_change_requests')
