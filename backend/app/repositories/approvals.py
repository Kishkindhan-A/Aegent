from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApprovalRequest


def get_approval_by_id_for_org(db: Session, *, approval_id: UUID, organization_id: UUID) -> ApprovalRequest | None:
    return db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.organization_id == organization_id,
        )
    ).scalar_one_or_none()


def list_approvals_for_org(
    db: Session,
    *,
    organization_id: UUID,
    offset: int,
    limit: int,
    status=None,
) -> tuple[list[ApprovalRequest], int]:
    filters = [ApprovalRequest.organization_id == organization_id]
    if status is not None:
        filters.append(ApprovalRequest.status == status)

    total = db.execute(select(ApprovalRequest).where(*filters)).scalars().all()
    total_count = len(total)
    approvals = db.execute(
        select(ApprovalRequest)
        .where(*filters)
        .order_by(ApprovalRequest.created_at.desc(), ApprovalRequest.id)
        .offset(offset)
        .limit(limit)
    ).scalars().all()
    return approvals, total_count
