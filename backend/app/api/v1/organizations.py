from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, require_roles
from app.database.session import get_db
from app.models import Organization, User
from app.models.enums import ActorType, AuditEventType, UserRole, UserStatus
from app.schemas.organization import (
    OrganizationMemberRoleUpdate,
    OrganizationMemberStatusUpdate,
    OrganizationRead,
    OrganizationSettingsUpdate,
)
from app.schemas.user import UserRead
from app.services.audit import record_audit_event

router = APIRouter(prefix='/organizations', tags=['organizations'])
MANAGEMENT_ROLES = (UserRole.OWNER, UserRole.ADMIN)


class OrganizationMemberListResponse(BaseModel):
    items: list[UserRead]
    total: int
    offset: int
    limit: int

    model_config = ConfigDict(from_attributes=True)


@router.get('/me', response_model=OrganizationRead)
def get_organization_me(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Organization:
    organization = db.get(Organization, current_user.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Organization not found.')
    return organization


@router.patch('/me', response_model=OrganizationRead)
def update_organization_me(
    payload: OrganizationSettingsUpdate,
    current_user: User = Depends(require_roles(UserRole.OWNER)),
    db: Session = Depends(get_db),
) -> Organization:
    organization = db.get(Organization, current_user.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Organization not found.')
    if payload.slug is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Organization slug is read-only.')
    if payload.status is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Organization status is managed automatically.')

    if payload.name is not None:
        organization.name = payload.name.strip()

    db.flush()
    record_audit_event(
        db,
        organization_id=organization.id,
        event_type=AuditEventType.ORGANIZATION_UPDATED,
        actor_type=ActorType.USER,
        source='organizations.settings',
        summary='Organization settings updated.',
        details={
            'organization_id': str(organization.id),
            'updated_by_user_id': str(current_user.id),
            'name': organization.name,
        },
        actor_user_id=current_user.id,
    )
    db.commit()
    db.refresh(organization)
    return organization


@router.get('/users', response_model=OrganizationMemberListResponse)
def list_members(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
) -> OrganizationMemberListResponse:
    stmt = select(User).where(User.organization_id == current_user.organization_id)
    total = db.scalar(select(func.count(User.id)).where(User.organization_id == current_user.organization_id)) or 0
    rows = db.execute(
        stmt.order_by(User.created_at.desc(), User.id)
        .offset(offset)
        .limit(limit)
    ).scalars().all()
    return OrganizationMemberListResponse(items=rows, total=total, offset=offset, limit=limit)


@router.get('/users/{user_id}', response_model=UserRead)
def get_member(
    user_id: UUID,
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
) -> User:
    target = db.execute(
        select(User).where(User.id == user_id, User.organization_id == current_user.organization_id)
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Member not found.')
    return target


@router.patch('/users/{user_id}/role', response_model=UserRead)
def update_member_role(
    user_id: UUID,
    payload: OrganizationMemberRoleUpdate,
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
) -> User:
    role = payload.role

    target = db.execute(
        select(User).where(User.id == user_id, User.organization_id == current_user.organization_id)
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Member not found.')
    if target.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You cannot change your own role.')
    if target.role == UserRole.OWNER or (current_user.role == UserRole.ADMIN and target.role == UserRole.OWNER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Owner role protection is enabled.')
    if role == UserRole.OWNER and current_user.role != UserRole.OWNER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only owners can assign the owner role.')

    old_role = target.role
    target.role = role
    db.flush()
    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        event_type=AuditEventType.USER_ROLE_CHANGED,
        actor_type=ActorType.USER,
        actor_user_id=current_user.id,
        source='organizations.membership',
        summary='Member role updated.',
        details={
            'target_user_id': str(target.id),
            'previous_role': old_role.value,
            'new_role': role.value,
        },
    )
    db.commit()
    db.refresh(target)
    return target


@router.patch('/users/{user_id}/status', response_model=UserRead)
def update_member_status(
    user_id: UUID,
    payload: OrganizationMemberStatusUpdate,
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
) -> User:
    status_value = payload.status

    target = db.execute(
        select(User).where(User.id == user_id, User.organization_id == current_user.organization_id)
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Member not found.')
    if target.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You cannot change your own status.')
    if target.role == UserRole.OWNER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Owner account status is protected.')

    old_status = target.status
    target.status = status_value
    db.flush()
    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        event_type=AuditEventType.USER_STATUS_CHANGED,
        actor_type=ActorType.USER,
        actor_user_id=current_user.id,
        source='organizations.membership',
        summary='Member status updated.',
        details={
            'target_user_id': str(target.id),
            'previous_status': old_status.value,
            'new_status': status_value.value,
        },
    )
    db.commit()
    db.refresh(target)
    return target
