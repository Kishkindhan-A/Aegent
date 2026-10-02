from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import OrganizationStatus, UserRole, UserStatus


class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=120)
    status: OrganizationStatus = OrganizationStatus.ACTIVE

    model_config = ConfigDict(from_attributes=True)


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    status: OrganizationStatus | None = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationSettingsUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    status: OrganizationStatus | None = None

    model_config = ConfigDict(from_attributes=True, extra='forbid')


class OrganizationMemberRoleUpdate(BaseModel):
    role: UserRole

    model_config = ConfigDict(from_attributes=True, extra='forbid')


class OrganizationMemberStatusUpdate(BaseModel):
    status: UserStatus

    model_config = ConfigDict(from_attributes=True, extra='forbid')


class OrganizationRead(OrganizationBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
