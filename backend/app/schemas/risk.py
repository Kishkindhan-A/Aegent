from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ActionType, AgentRiskLevel, DataSensitivity, Environment, PrivilegeLevel


class RiskFactor(BaseModel):
    factor: str = Field(..., min_length=1, max_length=120)
    weight: int = Field(..., ge=0, le=100)
    reason: str = Field(..., min_length=1, max_length=400)

    model_config = ConfigDict(from_attributes=True)


class RiskActionSummary(BaseModel):
    action_type: ActionType
    resource_type: str = Field(..., min_length=1, max_length=100)
    operation: str = Field(..., min_length=1, max_length=200)
    environment: Environment
    data_sensitivity: DataSensitivity
    privilege_level: PrivilegeLevel
    external_network_access: bool
    write_capability: bool
    destructive_capability: bool
    credential_access: bool
    financial_impact: bool
    requires_human_approval: bool

    @field_validator('resource_type', 'operation')
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError('Value must not be blank.')
        return normalized

    model_config = ConfigDict(from_attributes=True, extra='forbid')


class ActionRiskInput(BaseModel):
    """Deterministic action risk input used for offline evaluation.

    Security-relevant flags are required so omission cannot artificially lower risk.
    The risk engine evaluates explicit, normalized action context only; it does not
    interpret client metadata as verified security facts.
    """

    action_type: ActionType
    resource_type: str = Field(..., min_length=1, max_length=100)
    operation: str = Field(..., min_length=1, max_length=200)
    environment: Environment
    data_sensitivity: DataSensitivity
    privilege_level: PrivilegeLevel
    external_network_access: bool = Field(...)
    write_capability: bool = Field(...)
    destructive_capability: bool = Field(...)
    credential_access: bool = Field(...)
    financial_impact: bool = Field(...)
    requires_human_approval: bool = Field(...)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator('resource_type', 'operation')
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError('Value must not be blank.')
        return normalized

    @field_validator('metadata')
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        forbidden_keys = {'score', 'risk_level', 'organization_id', 'agent_id', 'decision', 'authorization'}
        sanitized = {key: val for key, val in value.items() if key not in forbidden_keys}

        if value and not sanitized:
            raise ValueError('Risk score, risk level, and authorization fields are server-derived.')

        return sanitized

    model_config = ConfigDict(from_attributes=True, extra='forbid')


RiskEvaluationRequest = ActionRiskInput


class RiskAssessmentResponse(BaseModel):
    agent_id: UUID | None = None
    action: RiskActionSummary
    score: int = Field(..., ge=0, le=100)
    risk_level: AgentRiskLevel
    factors: list[dict[str, Any]]
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)
