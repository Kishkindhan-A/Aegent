from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, require_roles
from app.database.session import get_db
from app.models import User
from app.models.enums import UserRole
from app.schemas.policy import PolicyCreate, PolicyListResponse, PolicyRead, PolicyUpdate
from app.services.policies import create_policy, disable_policy, get_policy, list_policies, update_policy

router = APIRouter(prefix='/policies', tags=['policies'])
MANAGEMENT_ROLES = (UserRole.OWNER, UserRole.ADMIN)


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Policy not found.')


@router.post('', response_model=PolicyRead, status_code=status.HTTP_201_CREATED)
def create_policy_endpoint(
    request: PolicyCreate,
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
) -> PolicyRead:
    return create_policy(db, organization_id=current_user.organization_id, current_user=current_user, data=request)


@router.get('', response_model=PolicyListResponse)
def list_policies_endpoint(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    enabled: bool | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PolicyListResponse:
    policies, total = list_policies(
        db,
        organization_id=current_user.organization_id,
        offset=offset,
        limit=limit,
        enabled=enabled,
    )
    return PolicyListResponse(items=policies, total=total, offset=offset, limit=limit)


@router.get('/{policy_id}', response_model=PolicyRead)
def get_policy_endpoint(
    policy_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PolicyRead:
    policy = get_policy(db, organization_id=current_user.organization_id, policy_id=policy_id)
    if policy is None:
        raise _not_found()
    return policy


@router.patch('/{policy_id}', response_model=PolicyRead)
def update_policy_endpoint(
    policy_id: UUID,
    request: PolicyUpdate,
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
) -> PolicyRead:
    policy = update_policy(
        db,
        organization_id=current_user.organization_id,
        policy_id=policy_id,
        data=request,
        actor_user_id=current_user.id,
    )
    if policy is None:
        raise _not_found()
    return policy


@router.post('/{policy_id}/disable', response_model=PolicyRead)
def disable_policy_endpoint(
    policy_id: UUID,
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
) -> PolicyRead:
    policy = disable_policy(db, organization_id=current_user.organization_id, policy_id=policy_id, actor_user_id=current_user.id)
    if policy is None:
        raise _not_found()
    return policy
