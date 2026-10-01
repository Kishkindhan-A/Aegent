from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import AgentRiskLevel, ApprovalStatus


class ApprovalRequest(Base):
    __tablename__ = 'approval_requests'
    __table_args__ = (
        Index('ix_approval_requests_organization_status', 'organization_id', 'status'),
        Index('ix_approval_requests_organization_agent', 'organization_id', 'agent_id'),
        Index('ix_approval_requests_org_agent_fingerprint', 'organization_id', 'agent_id', 'request_fingerprint'),
        Index('ix_approval_requests_expires_at', 'expires_at'),
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
    agent_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey('agents.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    requested_by_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    policy_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey('policies.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name='approval_status', native_enum=True, validate_strings=True),
        nullable=False,
        default=ApprovalStatus.PENDING,
        server_default='PENDING',
    )
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_level: Mapped[AgentRiskLevel] = mapped_column(
        Enum(AgentRiskLevel, name='approval_risk_level', native_enum=True, validate_strings=True),
        nullable=False,
        default=AgentRiskLevel.LOW,
        server_default='LOW',
    )
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    normalized_action_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    resolution_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    organization: Mapped['Organization'] = relationship(back_populates='approval_requests')
    agent: Mapped['Agent'] = relationship(back_populates='approval_requests')
    policy: Mapped['Policy | None'] = relationship(back_populates='approval_requests')
    requested_by_user: Mapped['User | None'] = relationship(
        back_populates='approval_requests_requested',
        foreign_keys='[ApprovalRequest.requested_by_user_id]',
    )
    resolved_by_user: Mapped['User | None'] = relationship(
        back_populates='approval_requests_resolved',
        foreign_keys='[ApprovalRequest.resolved_by_user_id]',
    )
    audit_events: Mapped[list['AuditEvent']] = relationship(back_populates='approval_request')
