"""phase14_organization_admin_audit_enum

Revision ID: d7ef2c4b9a10
Revises: a1c2d3e4f5b6
Create Date: 2026-10-02 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = 'd7ef2c4b9a10'
down_revision: Union[str, None] = 'a1c2d3e4f5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE audit_event_type ADD VALUE IF NOT EXISTS 'ORGANIZATION_UPDATED';")
    op.execute("ALTER TYPE audit_event_type ADD VALUE IF NOT EXISTS 'USER_ROLE_CHANGED';")
    op.execute("ALTER TYPE audit_event_type ADD VALUE IF NOT EXISTS 'USER_STATUS_CHANGED';")
    op.execute("ALTER TYPE audit_event_category ADD VALUE IF NOT EXISTS 'ADMINISTRATION';")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed directly without recreating the type,
    # so the downgrade path intentionally leaves the values in place for safety.
    pass
