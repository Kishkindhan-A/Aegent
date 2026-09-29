"""phase7_policy_and_approval

Revision ID: f4e9a2b7ab31
Revises: e5a1f2c3d4b5
Create Date: 2026-09-29 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = 'f4e9a2b7ab31'
down_revision: Union[str, None] = 'e5a1f2c3d4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    policy_effect = postgresql.ENUM(
        'ALLOW', 'DENY', 'REQUIRE_APPROVAL',
        name='policy_effect',
        create_type=False,
    )
    approval_status = postgresql.ENUM(
        'PENDING', 'APPROVED', 'REJECTED', 'EXPIRED',
        name='approval_status',
        create_type=False,
    )
    approval_risk_level = postgresql.ENUM(
        'LOW', 'MEDIUM', 'HIGH', 'CRITICAL',
        name='approval_risk_level',
        create_type=False,
    )
    policy_effect.create(bind, checkfirst=True)
    approval_status.create(bind, checkfirst=True)
    approval_risk_level.create(bind, checkfirst=True)

    op.create_table(
        'policies',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('effect', policy_effect, nullable=False, server_default='DENY'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_by_user_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('priority >= 0 AND priority <= 1000', name='ck_policies_priority_range'),
    )
    op.create_index('ix_policies_organization_id', 'policies', ['organization_id'], unique=False)
    op.create_index('ix_policies_organization_enabled_priority', 'policies', ['organization_id', 'enabled', 'priority'], unique=False)
    op.create_index('ix_policies_organization_created_at', 'policies', ['organization_id', 'created_at'], unique=False)
    op.create_index('ix_policies_created_by_user_id', 'policies', ['created_by_user_id'], unique=False)

    op.create_table(
        'approval_requests',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('agent_id', sa.UUID(), nullable=False),
        sa.Column('requested_by_user_id', sa.UUID(), nullable=True),
        sa.Column('policy_id', sa.UUID(), nullable=True),
        sa.Column('status', approval_status, nullable=False, server_default='PENDING'),
        sa.Column('risk_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('risk_level', approval_risk_level, nullable=False, server_default='LOW'),
        sa.Column('request_fingerprint', sa.String(length=64), nullable=False),
        sa.Column('normalized_action_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('resolution_reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resolved_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_approval_requests_organization_id', 'approval_requests', ['organization_id'], unique=False)
    op.create_index('ix_approval_requests_organization_status', 'approval_requests', ['organization_id', 'status'], unique=False)
    op.create_index('ix_approval_requests_organization_agent', 'approval_requests', ['organization_id', 'agent_id'], unique=False)
    op.create_index('ix_approval_requests_org_agent_fingerprint', 'approval_requests', ['organization_id', 'agent_id', 'request_fingerprint'], unique=False)
    op.create_index('ix_approval_requests_expires_at', 'approval_requests', ['expires_at'], unique=False)
    op.create_index('ix_approval_requests_requested_by_user_id', 'approval_requests', ['requested_by_user_id'], unique=False)
    op.create_index('ix_approval_requests_policy_id', 'approval_requests', ['policy_id'], unique=False)
    op.create_index('ix_approval_requests_resolved_by_user_id', 'approval_requests', ['resolved_by_user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_approval_requests_resolved_by_user_id', table_name='approval_requests')
    op.drop_index('ix_approval_requests_policy_id', table_name='approval_requests')
    op.drop_index('ix_approval_requests_requested_by_user_id', table_name='approval_requests')
    op.drop_index('ix_approval_requests_expires_at', table_name='approval_requests')
    op.drop_index('ix_approval_requests_org_agent_fingerprint', table_name='approval_requests')
    op.drop_index('ix_approval_requests_organization_agent', table_name='approval_requests')
    op.drop_index('ix_approval_requests_organization_status', table_name='approval_requests')
    op.drop_index('ix_approval_requests_organization_id', table_name='approval_requests')
    op.drop_table('approval_requests')

    op.drop_index('ix_policies_created_by_user_id', table_name='policies')
    op.drop_index('ix_policies_organization_created_at', table_name='policies')
    op.drop_index('ix_policies_organization_enabled_priority', table_name='policies')
    op.drop_index('ix_policies_organization_id', table_name='policies')
    op.drop_table('policies')

    bind = op.get_bind()
    postgresql.ENUM(name='approval_risk_level').drop(bind, checkfirst=True)
    postgresql.ENUM(name='approval_status').drop(bind, checkfirst=True)
    postgresql.ENUM(name='policy_effect').drop(bind, checkfirst=True)
