"""create repositories table

Revision ID: 001_create_repositories
Revises: 
Create Date: 2026-10-25 23:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_create_repositories'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'repositories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=1024), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False, server_default='git'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='registered'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_repositories'))
    )
    op.create_index(op.f('ix_repositories_name'), 'repositories', ['name'], unique=False)
    op.create_index(op.f('ix_repositories_status'), 'repositories', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_repositories_status'), table_name='repositories')
    op.drop_index(op.f('ix_repositories_name'), table_name='repositories')
    op.drop_table('repositories')
