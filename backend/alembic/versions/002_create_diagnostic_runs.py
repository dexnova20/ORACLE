"""create diagnostic_runs table

Revision ID: 002_create_diagnostic_runs
Revises: 001_create_repositories
Create Date: 2026-10-26 01:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_create_diagnostic_runs'
down_revision: Union[str, None] = '001_create_repositories'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'diagnostic_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('repository_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='completed'),
        sa.Column('commit_hash', sa.String(length=64), nullable=True),
        sa.Column('summary', sa.String(length=1024), nullable=True),
        sa.Column('report_json', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_diagnostic_runs'))
    )
    op.create_index(op.f('ix_diagnostic_runs_repository_id'), 'diagnostic_runs', ['repository_id'], unique=False)
    op.create_index(op.f('ix_diagnostic_runs_status'), 'diagnostic_runs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_diagnostic_runs_status'), table_name='diagnostic_runs')
    op.drop_index(op.f('ix_diagnostic_runs_repository_id'), table_name='diagnostic_runs')
    op.drop_table('diagnostic_runs')
