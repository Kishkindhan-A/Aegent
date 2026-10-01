from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Policy


def create_policy(
    db: Session,
    *,
    organization_id: UUID,
    name: str,
    description: str | None,
    effect,
    priority: int,
    enabled: bool,
    conditions: dict,
    created_by_user_id: UUID | None,
) -> Policy:
    policy = Policy(
        organization_id=organization_id,
        name=name,
        description=description,
        effect=effect,
        priority=priority,
        enabled=enabled,
        conditions=conditions,
        created_by_user_id=created_by_user_id,
    )
    db.add(policy)
    db.flush()
    return policy


def get_policy_by_id_for_org(db: Session, *, policy_id: UUID, organization_id: UUID) -> Policy | None:
    return db.execute(
        select(Policy).where(
            Policy.id == policy_id,
            Policy.organization_id == organization_id,
        )
    ).scalar_one_or_none()


def list_policies_for_org(
    db: Session,
    *,
    organization_id: UUID,
    offset: int,
    limit: int,
    enabled_only: bool = False,
    enabled: bool | None = None,
) -> tuple[list[Policy], int]:
    filters = [Policy.organization_id == organization_id]
    if enabled is not None:
        filters.append(Policy.enabled.is_(enabled))
    elif enabled_only:
        filters.append(Policy.enabled.is_(True))

    total = db.scalar(select(func.count(Policy.id)).where(*filters)) or 0
    policies = db.execute(
        select(Policy)
        .where(*filters)
        .order_by(Policy.priority.desc(), Policy.created_at.desc(), Policy.id)
        .offset(offset)
        .limit(limit)
    ).scalars().all()
    return policies, total


def update_policy_for_org(
    db: Session,
    *,
    policy_id: UUID,
    organization_id: UUID,
    updates: dict,
) -> Policy | None:
    policy = get_policy_by_id_for_org(db, policy_id=policy_id, organization_id=organization_id)
    if policy is None:
        return None
    for field, value in updates.items():
        setattr(policy, field, value)
    db.flush()
    return policy
