from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import ActorType, AuditEventCategory, AuditEventType, EventSeverity


def _category_for_event_type(event_type: AuditEventType) -> AuditEventCategory:
    mapping = {
        AuditEventType.AUTH_LOGIN_SUCCESS: AuditEventCategory.AUTHENTICATION,
        AuditEventType.AUTH_LOGOUT: AuditEventCategory.AUTHENTICATION,
        AuditEventType.AGENT_CREATED: AuditEventCategory.AGENT,
        AuditEventType.AGENT_UPDATED: AuditEventCategory.AGENT,
        AuditEventType.AGENT_DISABLED: AuditEventCategory.AGENT,
        AuditEventType.RISK_EVALUATED: AuditEventCategory.RISK,
        AuditEventType.POLICY_CREATED: AuditEventCategory.POLICY,
        AuditEventType.POLICY_UPDATED: AuditEventCategory.POLICY,
        AuditEventType.POLICY_DISABLED: AuditEventCategory.POLICY,
        AuditEventType.AUTHORIZATION_EVALUATED: AuditEventCategory.AUTHORIZATION,
        AuditEventType.APPROVAL_REQUESTED: AuditEventCategory.APPROVAL,
        AuditEventType.APPROVAL_APPROVED: AuditEventCategory.APPROVAL,
        AuditEventType.APPROVAL_REJECTED: AuditEventCategory.APPROVAL,
        AuditEventType.APPROVAL_EXPIRED: AuditEventCategory.APPROVAL,
        AuditEventType.PROMPT_INJECTION_DETECTED: AuditEventCategory.SECURITY,
        AuditEventType.SENSITIVE_DATA_DETECTED: AuditEventCategory.SECURITY,
        AuditEventType.POLICY_VIOLATION: AuditEventCategory.SECURITY,
        AuditEventType.ANOMALOUS_AGENT_BEHAVIOR: AuditEventCategory.SECURITY,
    }
    return mapping.get(event_type, AuditEventCategory.SECURITY)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace('-', '_').replace(' ', '_')
    sensitive_words = (
        'password',
        'password_hash',
        'token',
        'access_token',
        'refresh_token',
        'authorization',
        'cookie',
        'secret',
        'api_key',
        'credential',
        'database_url',
        'jwt_secret',
        'databasepassword',
    )
    return any(word in normalized for word in sensitive_words)


def _sanitize_detail_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, nested in value.items():
            if _is_sensitive_key(str(key)):
                continue
            sanitized[str(key)] = _sanitize_detail_value(nested)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_detail_value(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_detail_value(item) for item in value]
    if isinstance(value, set):
        return [_sanitize_detail_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _sanitize_details(details: Any) -> dict[str, Any]:
    if details is None:
        return {}
    if not isinstance(details, (dict, list, tuple, set)):
        details = {'value': details}
    sanitized = _sanitize_detail_value(details)
    if isinstance(sanitized, dict):
        return sanitized
    return {'value': sanitized}


class AuditEvent(Base):
    __tablename__ = 'audit_events'
    __table_args__ = (
        Index('ix_audit_events_org_created_at', 'organization_id', 'created_at'),
        Index('ix_audit_events_org_event_type', 'organization_id', 'event_type'),
        Index('ix_audit_events_org_severity', 'organization_id', 'severity'),
        Index('ix_audit_events_agent_id', 'agent_id'),
        Index('ix_audit_events_correlation_id', 'correlation_id'),
        Index('ix_audit_events_approval_request_id', 'approval_request_id'),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey('organizations.id', ondelete='RESTRICT'),
        nullable=False,
        index=True,
    )
    event_type: Mapped[AuditEventType] = mapped_column(
        Enum(AuditEventType, name='audit_event_type', native_enum=True, validate_strings=True),
        nullable=False,
        index=True,
    )
    category: Mapped[AuditEventCategory] = mapped_column(
        Enum(AuditEventCategory, name='audit_event_category', native_enum=True, validate_strings=True),
        nullable=False,
        index=True,
    )
    severity: Mapped[EventSeverity] = mapped_column(
        Enum(EventSeverity, name='event_severity', native_enum=True, validate_strings=True),
        nullable=False,
        index=True,
        default=EventSeverity.INFO,
        server_default='INFO',
    )
    actor_type: Mapped[ActorType] = mapped_column(
        Enum(ActorType, name='actor_type', native_enum=True, validate_strings=True),
        nullable=False,
        default=ActorType.SYSTEM,
        server_default='SYSTEM',
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    agent_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey('agents.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    policy_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey('policies.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    approval_request_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey('approval_requests.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default='{}')
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    def __init__(
        self,
        *,
        organization_id: UUID,
        event_type: AuditEventType,
        category: AuditEventCategory | None = None,
        severity: EventSeverity = EventSeverity.INFO,
        actor_type: ActorType = ActorType.SYSTEM,
        actor_user_id: UUID | None = None,
        agent_id: UUID | None = None,
        policy_id: UUID | None = None,
        approval_request_id: UUID | None = None,
        correlation_id: str | None = None,
        request_id: str | None = None,
        source: str,
        summary: str,
        details: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ):
        self.organization_id = organization_id
        self.event_type = event_type
        self.category = category if category is not None else _category_for_event_type(event_type)
        if self.category != _category_for_event_type(event_type):
            self.category = _category_for_event_type(event_type)
        self.severity = severity
        self.actor_type = actor_type
        self.actor_user_id = actor_user_id
        self.agent_id = agent_id
        self.policy_id = policy_id
        self.approval_request_id = approval_request_id
        self.correlation_id = correlation_id
        self.request_id = request_id
        self.source = source
        self.summary = summary
        self.details = _sanitize_details(details or {})
        self.created_at = created_at or datetime.now(timezone.utc)

    organization: Mapped['Organization'] = relationship(back_populates='audit_events')
    actor_user: Mapped['User | None'] = relationship(back_populates='audit_events')
    agent: Mapped['Agent | None'] = relationship(back_populates='audit_events')
    policy: Mapped['Policy | None'] = relationship(back_populates='audit_events')
    approval_request: Mapped['ApprovalRequest | None'] = relationship(back_populates='audit_events')
