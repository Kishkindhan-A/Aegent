from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr

from app.models.enums import UserRole, UserStatus


class RegisterRequest(BaseModel):
    organization_name: str = Field(..., min_length=1, max_length=255)
    organization_slug: str | None = Field(default=None, min_length=1, max_length=120)
    owner_email: EmailStr
    owner_full_name: str = Field(..., min_length=1, max_length=255)
    password: SecretStr = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr = Field(..., min_length=8, max_length=128)
    organization_slug: str | None = Field(default=None, min_length=1, max_length=120)
    organization_id: UUID | None = None


class RefreshRequest(BaseModel):
    refresh_token: SecretStr = Field(..., min_length=16, max_length=512)


class LogoutRequest(BaseModel):
    refresh_token: SecretStr = Field(..., min_length=16, max_length=512)


class CurrentUserResponse(BaseModel):
    id: UUID
    organization_id: UUID
    email: EmailStr
    full_name: str | None = None
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    expires_in: int
    user: CurrentUserResponse


class AuthStatusResponse(BaseModel):
    status: str
    message: str | None = None
