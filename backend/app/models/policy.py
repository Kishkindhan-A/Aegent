from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import PolicyEffect


class Policy(Base):
    __tablename__ = 'policies'
    __table_args__ = (
        Index('ix_policies_organization_enabled_priority', 'organization_id', 'enabled', 'priority'),
        Index('ix_policies_organization_created_at', 'organization_id', 'created_at'),
        CheckConstraint('priority >= 0 AND priority <= 1000', name='ck_policies_priority_range'),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey('organizations.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    effect: Mapped[PolicyEffect] = mapped_column(
        Enum(PolicyEffect, name='policy_effect', native_enum=True, validate_strings=True),
        nullable=False,
        default=PolicyEffect.DENY,
        server_default='DENY',
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default='true')
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default='100')
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    organization: Mapped['Organization'] = relationship(back_populates='policies')
    created_by_user: Mapped['User | None'] = relationship(back_populates='policies')
    approval_requests: Mapped[list['ApprovalRequest']] = relationship(back_populates='policy')
    audit_events: Mapped[list['AuditEvent']] = relationship(back_populates='policy')
