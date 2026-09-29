from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AgentRiskLevel, ApprovalStatus


class ApprovalResolutionRequest(BaseModel):
    resolution_reason: str | None = Field(default=None, max_length=2000)

    model_config = ConfigDict(from_attributes=True, extra='forbid')


class ApprovalRequestRead(BaseModel):
    id: UUID
    organization_id: UUID
    agent_id: UUID
    requested_by_user_id: UUID | None = None
    policy_id: UUID | None = None
    status: ApprovalStatus
    risk_score: int
    risk_level: AgentRiskLevel
    request_fingerprint: str
    normalized_action_snapshot: dict[str, Any]
    created_at: datetime
    expires_at: datetime
    resolved_at: datetime | None = None
    resolved_by_user_id: UUID | None = None
    resolution_reason: str | None = None

    model_config = ConfigDict(from_attributes=True, extra='forbid')


class ApprovalListResponse(BaseModel):
    items: list[ApprovalRequestRead]
    total: int
    offset: int
    limit: int

    model_config = ConfigDict(from_attributes=True, extra='forbid')
