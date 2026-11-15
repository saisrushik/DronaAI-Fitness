"""auth sessions, keep plans when a coach is deleted, allow account deletion

Revision ID: e1f3a5b7c9d2
Revises: c7f2d4e6a8b0
Create Date: 2026-11-15 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f3a5b7c9d2'
down_revision: Union[str, None] = 'c7f2d4e6a8b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables whose coach_id switches from CASCADE to SET NULL, so a coach deleting their account
# doesn't take their former customers' plans and request history with them.
_COACH_LINKED = ('workout_diet_plans', 'customer_requests')

# The least-privilege app role (scripts/create_app_role.py) may not exist, e.g. in CI.
_APP_ROLE = 'fitness_app'


def _coach_fk_name(table: str) -> str:
    # customer_requests was renamed from diet_change_requests, so its FK kept the old name.
    return op.get_bind().execute(
        sa.text(
            """
            SELECT con.conname
            FROM pg_constraint con
            JOIN pg_attribute att
              ON att.attrelid = con.conrelid AND att.attnum = ANY (con.conkey)
            WHERE con.conrelid = CAST(:table AS regclass)
              AND con.contype = 'f'
              AND att.attname = 'coach_id'
            """
        ),
        {'table': table},
    ).scalar_one()


def _relink_coach(table: str, ondelete: str) -> None:
    op.drop_constraint(_coach_fk_name(table), table, type_='foreignkey')
    op.create_foreign_key(
        f'{table}_coach_id_fkey', table, 'coaches', ['coach_id'], ['id'], ondelete=ondelete
    )


def _app_role_grant(statement: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{_APP_ROLE}') THEN
                {statement};
            END IF;
        END
        $$;
        """
    )


def upgrade() -> None:
    op.create_table(
        'auth_sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('refresh_jti', sa.String(length=64), nullable=False),
        sa.Column('previous_jti', sa.String(length=64), nullable=True),
        sa.Column('rotated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_auth_sessions_user_id'), 'auth_sessions', ['user_id'], unique=False)

    for table in _COACH_LINKED:
        op.alter_column(table, 'coach_id', nullable=True, existing_type=sa.UUID())
        _relink_coach(table, 'SET NULL')

    # Account deletion removes the users row; foreign keys cascade to everything else, and
    # cascades run with the table owner's rights, so no other table needs DELETE.
    _app_role_grant(f'GRANT DELETE ON TABLE users TO {_APP_ROLE}')


def downgrade() -> None:
    _app_role_grant(f'REVOKE DELETE ON TABLE users FROM {_APP_ROLE}')

    for table in _COACH_LINKED:
        # The old schema can't represent rows whose coach deleted their account.
        op.execute(f'DELETE FROM {table} WHERE coach_id IS NULL')
        _relink_coach(table, 'CASCADE')
        op.alter_column(table, 'coach_id', nullable=False, existing_type=sa.UUID())

    op.drop_index(op.f('ix_auth_sessions_user_id'), table_name='auth_sessions')
    op.drop_table('auth_sessions')
