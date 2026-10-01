from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditEvent
from app.models.enums import AuditEventType, EventSeverity


def get_audit_event_for_org(db: Session, *, event_id: UUID, organization_id: UUID) -> AuditEvent | None:
    return db.execute(
        select(AuditEvent).where(
            AuditEvent.id == event_id,
            AuditEvent.organization_id == organization_id,
        )
    ).scalar_one_or_none()


def list_audit_events_for_org(
    db: Session,
    *,
    organization_id: UUID,
    offset: int,
    limit: int,
    event_type: AuditEventType | None = None,
    severity: EventSeverity | None = None,
    actor_user_id: UUID | None = None,
    agent_id: UUID | None = None,
    policy_id: UUID | None = None,
    approval_request_id: UUID | None = None,
    correlation_id: str | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
) -> tuple[list[AuditEvent], int]:
    filters = [AuditEvent.organization_id == organization_id]
    if event_type is not None:
        filters.append(AuditEvent.event_type == event_type)
    if severity is not None:
        filters.append(AuditEvent.severity == severity)
    if actor_user_id is not None:
        filters.append(AuditEvent.actor_user_id == actor_user_id)
    if agent_id is not None:
        filters.append(AuditEvent.agent_id == agent_id)
    if policy_id is not None:
        filters.append(AuditEvent.policy_id == policy_id)
    if approval_request_id is not None:
        filters.append(AuditEvent.approval_request_id == approval_request_id)
    if correlation_id is not None:
        filters.append(AuditEvent.correlation_id == correlation_id)
    if created_after is not None:
        filters.append(AuditEvent.created_at >= created_after)
    if created_before is not None:
        filters.append(AuditEvent.created_at <= created_before)

    total = db.scalar(select(func.count(AuditEvent.id)).where(*filters)) or 0
    rows = db.execute(
        select(AuditEvent)
        .where(*filters)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .offset(offset)
        .limit(limit)
    ).scalars().all()
    return rows, total
