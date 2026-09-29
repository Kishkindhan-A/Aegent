from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ActionType, AgentRiskLevel, AgentType, DataSensitivity, Environment, PolicyEffect, PrivilegeLevel


class PolicyConditions(BaseModel):
    agent_id: UUID | None = None
    agent_type: AgentType | None = None
    action_type: ActionType | None = None
    environment: Environment | None = None
    data_sensitivity: DataSensitivity | None = None
    privilege_level: PrivilegeLevel | None = None
    minimum_risk_score: int | None = Field(default=None, ge=0, le=100)
    minimum_risk_level: AgentRiskLevel | None = None
    external_network_access: bool | None = None
    destructive_capability: bool | None = None
    credential_access: bool | None = None
    financial_impact: bool | None = None

    model_config = ConfigDict(from_attributes=True, extra='forbid')

    @field_validator('agent_id')
    @classmethod
    def validate_agent_id(cls, value: UUID | None) -> UUID | None:
        if value is None:
            return value
        return value


class PolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    effect: PolicyEffect
    enabled: bool = True
    priority: int = Field(default=100, ge=0, le=1000)
    conditions: PolicyConditions = Field(default_factory=PolicyConditions)

    @field_validator('name')
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError('Policy name must not be blank.')
        return normalized

    model_config = ConfigDict(from_attributes=True, extra='forbid')


class PolicyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    effect: PolicyEffect | None = None
    enabled: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=1000)
    conditions: PolicyConditions | None = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError('Policy name must not be blank.')
        return normalized

    model_config = ConfigDict(from_attributes=True, extra='forbid')


class PolicyRead(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None = None
    effect: PolicyEffect
    enabled: bool
    priority: int
    conditions: PolicyConditions
    created_by_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, extra='forbid')


class PolicyListResponse(BaseModel):
    items: list[PolicyRead]
    total: int
    offset: int
    limit: int


class PolicyDecisionResult(BaseModel):
    decision: PolicyEffect
    matched_policy_id: UUID | None = None
    matched_policy_name: str | None = None
    matched_policy_effect: PolicyEffect | None = None
    priority: int | None = None
    reason: str
    risk_score: int | None = None
    risk_level: str | None = None
    matched_details: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True, extra='forbid')


class AuthorizationDecisionResponse(BaseModel):
    decision: PolicyEffect
    risk: dict[str, Any]
    matched_policy: dict[str, Any] | None = None
    reason: str
    approval_request_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True, extra='forbid')
