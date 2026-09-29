from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, require_roles
from app.database.session import get_db
from app.models import User
from app.models.enums import ApprovalStatus, UserRole
from app.schemas.approval import ApprovalListResponse, ApprovalRequestRead, ApprovalResolutionRequest
from app.services.approvals import approve_approval_request, get_approval, list_approvals, reject_approval_request

router = APIRouter(prefix='/approvals', tags=['approvals'])
REVIEW_ROLES = (UserRole.OWNER, UserRole.ADMIN, UserRole.SECURITY_ANALYST)


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Approval request not found.')


@router.get('', response_model=ApprovalListResponse)
def list_approvals_endpoint(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status: ApprovalStatus | None = None,
    current_user: User = Depends(require_roles(*REVIEW_ROLES)),
    db: Session = Depends(get_db),
) -> ApprovalListResponse:
    approvals, total = list_approvals(
        db,
        organization_id=current_user.organization_id,
        offset=offset,
        limit=limit,
        status=status,
    )
    return ApprovalListResponse(items=approvals, total=total, offset=offset, limit=limit)


@router.get('/{approval_id}', response_model=ApprovalRequestRead)
def get_approval_endpoint(
    approval_id: UUID,
    current_user: User = Depends(require_roles(*REVIEW_ROLES)),
    db: Session = Depends(get_db),
) -> ApprovalRequestRead:
    approval = get_approval(db, organization_id=current_user.organization_id, approval_id=approval_id)
    if approval is None:
        raise _not_found()
    return approval


@router.post('/{approval_id}/approve', response_model=ApprovalRequestRead)
def approve_approval_endpoint(
    approval_id: UUID,
    request: ApprovalResolutionRequest,
    current_user: User = Depends(require_roles(*REVIEW_ROLES)),
    db: Session = Depends(get_db),
) -> ApprovalRequestRead:
    return approve_approval_request(
        db,
        organization_id=current_user.organization_id,
        approval_id=approval_id,
        reviewer=current_user,
        resolution_reason=request.resolution_reason,
    )


@router.post('/{approval_id}/reject', response_model=ApprovalRequestRead)
def reject_approval_endpoint(
    approval_id: UUID,
    request: ApprovalResolutionRequest,
    current_user: User = Depends(require_roles(*REVIEW_ROLES)),
    db: Session = Depends(get_db),
) -> ApprovalRequestRead:
    return reject_approval_request(
        db,
        organization_id=current_user.organization_id,
        approval_id=approval_id,
        reviewer=current_user,
        resolution_reason=request.resolution_reason,
    )
