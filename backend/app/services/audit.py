from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import AuditEvent
from app.models.enums import ActorType, AuditEventCategory, AuditEventType, EventSeverity
from app.repositories.audit_events import get_audit_event_for_org, list_audit_events_for_org

MAX_AUDIT_DETAILS_BYTES = 65536
SENSITIVE_KEYWORDS = (
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


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace('-', '_').replace(' ', '_')
    return any(sensitive in normalized for sensitive in SENSITIVE_KEYWORDS)


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, nested in value.items():
            if _is_sensitive_key(str(key)):
                continue
            sanitized[str(key)] = _sanitize_value(nested)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, set):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def sanitize_audit_details(details: Any, *, max_bytes: int = MAX_AUDIT_DETAILS_BYTES) -> dict[str, Any]:
    if details is None:
        return {}
    if not isinstance(details, (dict, list, tuple, set)):
        details = {'value': details}
    sanitized = _sanitize_value(details)
    serialized = json.dumps(sanitized, separators=(',', ':'), ensure_ascii=True, default=str)
    if len(serialized.encode('utf-8')) > max_bytes:
        truncated = json.loads(serialized)
        return {'truncated': True, 'value': truncated if isinstance(truncated, dict) else {'value': truncated}}
    return sanitized if isinstance(sanitized, dict) else {'value': sanitized}


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


def _severity_for_event_type(event_type: AuditEventType) -> EventSeverity:
    mapping = {
        AuditEventType.AUTH_LOGIN_SUCCESS: EventSeverity.INFO,
        AuditEventType.AUTH_LOGOUT: EventSeverity.INFO,
        AuditEventType.AGENT_CREATED: EventSeverity.INFO,
        AuditEventType.AGENT_UPDATED: EventSeverity.INFO,
        AuditEventType.AGENT_DISABLED: EventSeverity.WARNING,
        AuditEventType.RISK_EVALUATED: EventSeverity.WARNING,
        AuditEventType.POLICY_CREATED: EventSeverity.INFO,
        AuditEventType.POLICY_UPDATED: EventSeverity.INFO,
        AuditEventType.POLICY_DISABLED: EventSeverity.WARNING,
        AuditEventType.AUTHORIZATION_EVALUATED: EventSeverity.WARNING,
        AuditEventType.APPROVAL_REQUESTED: EventSeverity.WARNING,
        AuditEventType.APPROVAL_APPROVED: EventSeverity.INFO,
        AuditEventType.APPROVAL_REJECTED: EventSeverity.HIGH,
        AuditEventType.APPROVAL_EXPIRED: EventSeverity.WARNING,
        AuditEventType.PROMPT_INJECTION_DETECTED: EventSeverity.CRITICAL,
        AuditEventType.SENSITIVE_DATA_DETECTED: EventSeverity.HIGH,
        AuditEventType.POLICY_VIOLATION: EventSeverity.CRITICAL,
        AuditEventType.ANOMALOUS_AGENT_BEHAVIOR: EventSeverity.CRITICAL,
    }
    return mapping.get(event_type, EventSeverity.INFO)


def record_audit_event(
    db: Session,
    *,
    organization_id: UUID,
    event_type: AuditEventType,
    actor_type: ActorType,
    source: str,
    summary: str,
    details: dict[str, Any] | None = None,
    actor_user_id: UUID | None = None,
    agent_id: UUID | None = None,
    policy_id: UUID | None = None,
    approval_request_id: UUID | None = None,
    correlation_id: str | None = None,
    request_id: str | None = None,
    category: AuditEventCategory | None = None,
    severity: EventSeverity | None = None,
) -> AuditEvent:
    event_category = category or _category_for_event_type(event_type)
    event_severity = severity or _severity_for_event_type(event_type)
    safe_summary = (summary or '').strip()
    if len(safe_summary) > 500:
        safe_summary = safe_summary[:497] + '...'
    if not safe_summary:
        safe_summary = event_type.value

    event = AuditEvent(
        organization_id=organization_id,
        event_type=event_type,
        category=event_category,
        severity=event_severity,
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        agent_id=agent_id,
        policy_id=policy_id,
        approval_request_id=approval_request_id,
        correlation_id=correlation_id,
        request_id=request_id,
        source=source[:64],
        summary=safe_summary,
        details=sanitize_audit_details(details or {}),
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    db.flush()
    return event


def list_audit_events(
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
    if created_after and created_before and created_after > created_before:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail='created_after must be before created_before.')
    return list_audit_events_for_org(
        db,
        organization_id=organization_id,
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


def get_audit_event(db: Session, *, organization_id: UUID, event_id: UUID) -> AuditEvent | None:
    return get_audit_event_for_org(db, event_id=event_id, organization_id=organization_id)
