from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, require_roles
from app.database.session import get_db
from app.models import User
from app.models.enums import AuditEventType, EventSeverity, UserRole
from app.schemas.audit import AuditEventListResponse, AuditEventRead
from app.services.audit import get_audit_event, list_audit_events

router = APIRouter(prefix='/audit', tags=['audit'])
READ_ROLES = (UserRole.OWNER, UserRole.ADMIN, UserRole.SECURITY_ANALYST)


@router.get('/events', response_model=AuditEventListResponse)
def list_audit_events_endpoint(
    event_type: AuditEventType | None = None,
    severity: EventSeverity | None = None,
    actor_user_id: UUID | None = None,
    agent_id: UUID | None = None,
    policy_id: UUID | None = None,
    approval_request_id: UUID | None = None,
    correlation_id: str | None = None,
    created_after: datetime | None = Query(default=None),
    created_before: datetime | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(require_roles(*READ_ROLES)),
    db: Session = Depends(get_db),
) -> AuditEventListResponse:
    events, total = list_audit_events(
        db,
        organization_id=current_user.organization_id,
        offset=offset,
        limit=limit,
        event_type=event_type,
        severity=severity,
        actor_user_id=actor_user_id,
        agent_id=agent_id,
        policy_id=policy_id,
        approval_request_id=approval_request_id,
        correlation_id=correlation_id,
        created_after=created_after,
        created_before=created_before,
    )
    return AuditEventListResponse(items=events, total=total, offset=offset, limit=limit)


@router.get('/events/{event_id}', response_model=AuditEventRead)
def get_audit_event_endpoint(
    event_id: UUID,
    current_user: User = Depends(require_roles(*READ_ROLES)),
    db: Session = Depends(get_db),
) -> AuditEventRead:
    event = get_audit_event(db, organization_id=current_user.organization_id, event_id=event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Audit event not found.')
    return event
