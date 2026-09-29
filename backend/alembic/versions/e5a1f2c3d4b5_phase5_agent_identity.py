"""phase5_agent_identity

Revision ID: e5a1f2c3d4b5
Revises: d1b3e62a3c77
Create Date: 2026-09-29 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = 'e5a1f2c3d4b5'
down_revision: Union[str, None] = 'd1b3e62a3c77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    agent_type = postgresql.ENUM(
        'GENERAL', 'CODING', 'DATA', 'SECURITY', 'AUTOMATION', 'CUSTOM',
        name='agent_type',
        create_type=False,
    )
    agent_status = postgresql.ENUM(
        'ACTIVE', 'DISABLED', 'SUSPENDED',
        name='agent_status',
        create_type=False,
    )
    agent_risk_level = postgresql.ENUM(
        'LOW', 'MEDIUM', 'HIGH', 'CRITICAL',
        name='agent_risk_level',
        create_type=False,
    )
    agent_type.create(bind, checkfirst=True)
    agent_status.create(bind, checkfirst=True)
    agent_risk_level.create(bind, checkfirst=True)

    op.create_table(
        'agents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('agent_type', agent_type, nullable=False, server_default='GENERAL'),
        sa.Column('status', agent_status, nullable=False, server_default='ACTIVE'),
        sa.Column('risk_level', agent_risk_level, nullable=False, server_default='LOW'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_agents_organization_id', 'agents', ['organization_id'], unique=False)
    op.create_index('ix_agents_organization_status', 'agents', ['organization_id', 'status'], unique=False)
    op.create_index('ix_agents_organization_agent_type', 'agents', ['organization_id', 'agent_type'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_agents_organization_agent_type', table_name='agents')
    op.drop_index('ix_agents_organization_status', table_name='agents')
    op.drop_index('ix_agents_organization_id', table_name='agents')
    op.drop_table('agents')
    bind = op.get_bind()
    postgresql.ENUM(name='agent_risk_level').drop(bind, checkfirst=True)
    postgresql.ENUM(name='agent_status').drop(bind, checkfirst=True)
    postgresql.ENUM(name='agent_type').drop(bind, checkfirst=True)