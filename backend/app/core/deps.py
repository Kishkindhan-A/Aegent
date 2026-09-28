from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import Organization, User
from app.models.enums import OrganizationStatus, UserRole, UserStatus
from app.security.tokens import decode_token

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Authentication required.',
        )

    payload = decode_token(credentials.credentials, expected_type='access')

    try:
        user_id = UUID(payload['sub'])
        organization_id = UUID(payload['organization_id'])
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Malformed token payload.',
        ) from None

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User not found.',
        )

    if user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Organization mismatch.',
        )

    if UserRole(payload.get('role', '')) != user.role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token role is invalid.',
        )

    if user.status not in {UserStatus.ACTIVE}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='User account is not active.',
        )

    organization = db.get(Organization, organization_id)
    if organization is None or organization.status != OrganizationStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Organization is not active.',
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Inactive user.',
        )
    return current_user


def require_roles(*allowed_roles: UserRole):
    async def role_dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Insufficient role permissions.',
            )
        return current_user

    return role_dependency
