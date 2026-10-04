"""add body measurements log

Revision ID: b3e8a1c5d7f9
Revises: 9d4b6f2a8c1e
Create Date: 2026-10-04 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3e8a1c5d7f9'
down_revision: Union[str, None] = '9d4b6f2a8c1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'body_measurements',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('customer_id', sa.UUID(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('weight_kg', sa.Float(), nullable=True),
        sa.Column('height_cm', sa.Float(), nullable=True),
        sa.Column('waist_cm', sa.Float(), nullable=True),
        sa.Column('neck_cm', sa.Float(), nullable=True),
        sa.Column('hip_cm', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_body_measurements_customer_id'), 'body_measurements', ['customer_id'], unique=False
    )
    # Start everyone's history from the measurements already on their profile.
    op.execute(
        """
        INSERT INTO body_measurements
            (id, customer_id, recorded_at, weight_kg, height_cm, waist_cm, neck_cm, hip_cm)
        SELECT gen_random_uuid(), id, now(), weight_kg, height_cm, waist_cm, neck_cm, hip_cm
        FROM customers
        WHERE COALESCE(weight_kg, height_cm, waist_cm, neck_cm, hip_cm) IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_body_measurements_customer_id'), table_name='body_measurements')
    op.drop_table('body_measurements')
