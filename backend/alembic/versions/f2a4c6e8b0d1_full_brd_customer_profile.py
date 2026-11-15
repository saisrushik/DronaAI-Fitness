"""full BRD profile: 8 goals, country, budget, stress, conditions, structured injuries,
workout preferences

Revision ID: f2a4c6e8b0d1
Revises: e1f3a5b7c9d2
Create Date: 2026-11-15 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f2a4c6e8b0d1'
down_revision: Union[str, None] = 'e1f3a5b7c9d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Old goal names that map one-to-one onto BRD goals.
_GOAL_RENAMES = {'build_muscle': 'lean_bulk', 'improve_endurance': 'endurance'}
# New goals with no old equivalent fall back to the closest old one on downgrade.
_GOAL_DOWNGRADES = {
    'lean_bulk': 'build_muscle',
    'aggressive_bulk': 'build_muscle',
    'strength': 'build_muscle',
    'endurance': 'improve_endurance',
    'recomp': 'maintain',
    'general_fitness': 'maintain',
}

# Checked in order, so "upper back" wins over the plain "back" keyword.
_BODY_PART_KEYWORDS = [
    ('upper_back', ('upper back',)),
    ('lower_back', ('lower back', 'back', 'spine', 'disc', 'lumbar')),
    ('knee', ('knee', 'acl', 'mcl', 'menisc')),
    ('shoulder', ('shoulder', 'rotator')),
    ('elbow', ('elbow',)),
    ('wrist', ('wrist', 'carpal')),
    ('hip', ('hip',)),
    ('ankle', ('ankle', 'achilles')),
    ('neck', ('neck', 'cervical')),
]

_customers = sa.table(
    'customers',
    sa.column('id', sa.UUID()),
    sa.column('injuries', postgresql.JSONB()),
)


def _body_part(text: str) -> str:
    lowered = text.lower()
    for part, keywords in _BODY_PART_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return part
    return 'other'


def _convert_injuries(convert) -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.select(_customers.c.id, _customers.c.injuries)).all()
    for customer_id, injuries in rows:
        if not injuries:
            continue
        bind.execute(
            _customers.update()
            .where(_customers.c.id == customer_id)
            .values(injuries=[convert(item) for item in injuries])
        )


def _to_record(item):
    if isinstance(item, dict):
        return item
    # Free text from the old form; the details weren't captured, so assume the mildest case.
    return {
        'body_part': _body_part(str(item)),
        'severity': 'mild',
        'recovery_status': 'recovering',
        'date_of_injury': None,
        'notes': str(item)[:200],
    }


def _to_text(item):
    if isinstance(item, dict):
        return item.get('notes') or str(item.get('body_part', 'injury')).replace('_', ' ')
    return item


def upgrade() -> None:
    op.add_column('customers', sa.Column('country', sa.String(length=2), server_default='IN', nullable=False))
    op.add_column('customers', sa.Column('budget_level', sa.String(length=10), nullable=True))
    op.add_column('customers', sa.Column('stress_level', sa.String(length=10), nullable=True))
    op.add_column('customers', sa.Column('training_experience', sa.String(length=20), nullable=True))
    op.add_column('customers', sa.Column('training_location', sa.String(length=10), nullable=True))
    op.add_column('customers', sa.Column('training_days_per_week', sa.Integer(), nullable=True))
    op.add_column('customers', sa.Column('medical_conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('customers', sa.Column('profile_updated_at', sa.DateTime(timezone=True), nullable=True))

    op.alter_column('customers', 'health_injury_history', new_column_name='injuries')
    _convert_injuries(_to_record)

    for old, new in _GOAL_RENAMES.items():
        op.execute(
            sa.text('UPDATE customers SET primary_goal = :new WHERE primary_goal = :old')
            .bindparams(old=old, new=new)
        )

    # Finished profiles get the values their current plans were built with (intermediate
    # volume at the gym; 3 days for maintain and 4 for every other old split). Otherwise the
    # form would show different defaults, and the first save would look like a change to the coach.
    op.execute(
        """
        UPDATE customers
        SET budget_level = 'medium',
            stress_level = 'medium',
            training_experience = 'intermediate',
            training_location = 'gym',
            training_days_per_week = CASE WHEN primary_goal = 'maintain' THEN 3 ELSE 4 END
        WHERE profile_completed
        """
    )


def downgrade() -> None:
    for new, old in _GOAL_DOWNGRADES.items():
        op.execute(
            sa.text('UPDATE customers SET primary_goal = :old WHERE primary_goal = :new')
            .bindparams(old=old, new=new)
        )

    _convert_injuries(_to_text)
    op.alter_column('customers', 'injuries', new_column_name='health_injury_history')

    op.drop_column('customers', 'profile_updated_at')
    op.drop_column('customers', 'medical_conditions')
    op.drop_column('customers', 'training_days_per_week')
    op.drop_column('customers', 'training_location')
    op.drop_column('customers', 'training_experience')
    op.drop_column('customers', 'stress_level')
    op.drop_column('customers', 'budget_level')
    op.drop_column('customers', 'country')
