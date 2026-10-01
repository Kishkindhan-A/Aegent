"""phase8_audit_event_foundation

Revision ID: a1c2d3e4f5b6
Revises: f4e9a2b7ab31
Create Date: 2026-10-01 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = 'a1c2d3e4f5b6'
down_revision: Union[str, None] = 'f4e9a2b7ab31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    audit_event_type = postgresql.ENUM(
        'AUTH_LOGIN_SUCCESS', 'AUTH_LOGOUT',
        'AGENT_CREATED', 'AGENT_UPDATED', 'AGENT_DISABLED',
        'RISK_EVALUATED',
        'POLICY_CREATED', 'POLICY_UPDATED', 'POLICY_DISABLED',
        'AUTHORIZATION_EVALUATED',
        'APPROVAL_REQUESTED', 'APPROVAL_APPROVED', 'APPROVAL_REJECTED', 'APPROVAL_EXPIRED',
        'PROMPT_INJECTION_DETECTED', 'SENSITIVE_DATA_DETECTED', 'POLICY_VIOLATION', 'ANOMALOUS_AGENT_BEHAVIOR',
        name='audit_event_type',
        create_type=False,
    )
    audit_event_category = postgresql.ENUM(
        'AUTHENTICATION', 'AGENT', 'RISK', 'POLICY', 'AUTHORIZATION', 'APPROVAL', 'SECURITY',
        name='audit_event_category',
        create_type=False,
    )
    event_severity = postgresql.ENUM(
        'INFO', 'WARNING', 'HIGH', 'CRITICAL',
        name='event_severity',
        create_type=False,
    )
    actor_type = postgresql.ENUM(
        'USER', 'AGENT', 'SYSTEM',
        name='actor_type',
        create_type=False,
    )
    audit_event_type.create(bind, checkfirst=True)
    audit_event_category.create(bind, checkfirst=True)
    event_severity.create(bind, checkfirst=True)
    actor_type.create(bind, checkfirst=True)

    op.create_table(
        'audit_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('event_type', audit_event_type, nullable=False),
        sa.Column('category', audit_event_category, nullable=False),
        sa.Column('severity', event_severity, nullable=False, server_default='INFO'),
        sa.Column('actor_type', actor_type, nullable=False, server_default='SYSTEM'),
        sa.Column('actor_user_id', sa.UUID(), nullable=True),
        sa.Column('agent_id', sa.UUID(), nullable=True),
        sa.Column('policy_id', sa.UUID(), nullable=True),
        sa.Column('approval_request_id', sa.UUID(), nullable=True),
        sa.Column('correlation_id', sa.String(length=128), nullable=True),
        sa.Column('request_id', sa.String(length=128), nullable=True),
        sa.Column('source', sa.String(length=64), nullable=False),
        sa.Column('summary', sa.String(length=500), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['approval_request_id'], ['approval_requests.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_events_organization_id', 'audit_events', ['organization_id'], unique=False)
    op.create_index('ix_audit_events_org_created_at', 'audit_events', ['organization_id', 'created_at'], unique=False)
    op.create_index('ix_audit_events_org_event_type', 'audit_events', ['organization_id', 'event_type'], unique=False)
    op.create_index('ix_audit_events_org_severity', 'audit_events', ['organization_id', 'severity'], unique=False)
    op.create_index('ix_audit_events_agent_id', 'audit_events', ['agent_id'], unique=False)
    op.create_index('ix_audit_events_correlation_id', 'audit_events', ['correlation_id'], unique=False)
    op.create_index('ix_audit_events_approval_request_id', 'audit_events', ['approval_request_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_audit_events_approval_request_id', table_name='audit_events')
    op.drop_index('ix_audit_events_correlation_id', table_name='audit_events')
    op.drop_index('ix_audit_events_agent_id', table_name='audit_events')
    op.drop_index('ix_audit_events_org_severity', table_name='audit_events')
    op.drop_index('ix_audit_events_org_event_type', table_name='audit_events')
    op.drop_index('ix_audit_events_org_created_at', table_name='audit_events')
    op.drop_index('ix_audit_events_organization_id', table_name='audit_events')
    op.drop_table('audit_events')

    bind = op.get_bind()
    postgresql.ENUM(name='actor_type').drop(bind, checkfirst=True)
    postgresql.ENUM(name='event_severity').drop(bind, checkfirst=True)
    postgresql.ENUM(name='audit_event_category').drop(bind, checkfirst=True)
    postgresql.ENUM(name='audit_event_type').drop(bind, checkfirst=True)
