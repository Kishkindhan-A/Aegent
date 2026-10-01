from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ActorType, AuditEventCategory, AuditEventType, EventSeverity


class AuditEventRead(BaseModel):
    id: UUID
    organization_id: UUID
    event_type: AuditEventType
    category: AuditEventCategory
    severity: EventSeverity
    actor_type: ActorType
    actor_user_id: UUID | None = None
    agent_id: UUID | None = None
    policy_id: UUID | None = None
    approval_request_id: UUID | None = None
    correlation_id: str | None = None
    request_id: str | None = None
    source: str
    summary: str = Field(..., max_length=500)
    details: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, extra='forbid')


class AuditEventListResponse(BaseModel):
    items: list[AuditEventRead]
    total: int
    offset: int
    limit: int

    model_config = ConfigDict(from_attributes=True, extra='forbid')
