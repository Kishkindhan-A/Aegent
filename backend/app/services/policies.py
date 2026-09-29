from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Policy, User
from app.models.enums import PolicyEffect
from app.repositories.policies import create_policy as repository_create_policy
from app.repositories.policies import get_policy_by_id_for_org, list_policies_for_org, update_policy_for_org
from app.schemas.policy import PolicyConditions, PolicyCreate, PolicyRead, PolicyUpdate


def _validate_conditions_raw(data: dict | PolicyConditions | None) -> dict:
    if data is None:
        return {}
    if isinstance(data, PolicyConditions):
        return data.model_dump(exclude_none=True, mode='json')
    return PolicyConditions.model_validate(data).model_dump(exclude_none=True, mode='json')


def create_policy(db: Session, *, organization_id: UUID, current_user: User, data: PolicyCreate) -> Policy:
    policy = repository_create_policy(
        db,
        organization_id=organization_id,
        name=data.name,
        description=data.description,
        effect=data.effect,
        priority=data.priority,
        enabled=data.enabled,
        conditions=_validate_conditions_raw(data.conditions),
        created_by_user_id=current_user.id,
    )
    db.commit()
    db.refresh(policy)
    return policy


def list_policies(
    db: Session,
    *,
    organization_id: UUID,
    offset: int,
    limit: int,
    enabled_only: bool = False,
) -> tuple[list[Policy], int]:
    return list_policies_for_org(
        db,
        organization_id=organization_id,
        offset=offset,
        limit=limit,
        enabled_only=enabled_only,
    )


def get_policy(db: Session, *, organization_id: UUID, policy_id: UUID) -> Policy | None:
    return get_policy_by_id_for_org(db, policy_id=policy_id, organization_id=organization_id)


def update_policy(db: Session, *, organization_id: UUID, policy_id: UUID, data: PolicyUpdate) -> Policy | None:
    updates = data.model_dump(exclude_unset=True)
    if 'conditions' in updates and updates['conditions'] is not None:
        updates['conditions'] = _validate_conditions_raw(updates['conditions'])
    policy = update_policy_for_org(
        db,
        policy_id=policy_id,
        organization_id=organization_id,
        updates=updates,
    )
    if policy is None:
        return None
    db.commit()
    db.refresh(policy)
    return policy


def disable_policy(db: Session, *, organization_id: UUID, policy_id: UUID) -> Policy | None:
    return update_policy(
        db,
        organization_id=organization_id,
        policy_id=policy_id,
        data=PolicyUpdate(enabled=False),
    )


def list_enabled_policies_for_org(db: Session, *, organization_id: UUID) -> list[Policy]:
    policies, _ = list_policies_for_org(db, organization_id=organization_id, offset=0, limit=1000, enabled_only=True)
    return policies
