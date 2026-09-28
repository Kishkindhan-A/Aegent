from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole, UserStatus


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None
    role: UserRole = UserRole.MEMBER
    status: UserStatus = UserStatus.ACTIVE

    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    organization_id: UUID
    password_hash: str = Field(..., min_length=1, max_length=255)


class UserUpdate(BaseModel):
    organization_id: UUID | None = None
    email: EmailStr | None = None
    password_hash: str | None = Field(default=None, min_length=1, max_length=255)
    full_name: str | None = None
    role: UserRole | None = None
    status: UserStatus | None = None

    model_config = ConfigDict(from_attributes=True)


class UserRead(UserBase):
    id: UUID
    organization_id: UUID
    created_at: datetime
    updated_at: datetime
