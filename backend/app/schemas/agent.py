from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AgentRiskLevel, AgentStatus, AgentType


class AgentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    agent_type: AgentType = AgentType.GENERAL

    @field_validator('name')
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError('Agent name must not be blank.')
        return normalized

    model_config = ConfigDict(from_attributes=True)


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    agent_type: AgentType | None = None
    status: AgentStatus | None = None
    risk_level: AgentRiskLevel | None = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError('Agent name must not be blank.')
        return normalized

    model_config = ConfigDict(from_attributes=True)


class AgentRead(AgentBase):
    id: UUID
    organization_id: UUID
    status: AgentStatus
    risk_level: AgentRiskLevel
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    items: list[AgentRead]
    total: int
    offset: int
    limit: int