from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import ApprovalRequest, Policy, User
from app.models.enums import ActorType, AgentRiskLevel, ApprovalStatus, AuditEventType, PolicyEffect
from app.services.audit import record_audit_event
from app.repositories.approvals import get_approval_by_id_for_org, list_approvals_for_org
from app.schemas.approval import ApprovalRequestRead, ApprovalResolutionRequest


def _normalize_snapshot(action_context: dict, risk_assessment: dict, policy: Policy) -> dict:
    snapshot = {
        'action_type': action_context.get('action_type'),
        'resource_type': action_context.get('resource_type'),
        'operation': action_context.get('operation'),
        'environment': action_context.get('environment'),
        'data_sensitivity': action_context.get('data_sensitivity'),
        'privilege_level': action_context.get('privilege_level'),
        'external_network_access': bool(action_context.get('external_network_access', False)),
        'destructive_capability': bool(action_context.get('destructive_capability', False)),
        'credential_access': bool(action_context.get('credential_access', False)),
        'financial_impact': bool(action_context.get('financial_impact', False)),
        'requires_human_approval': bool(action_context.get('requires_human_approval', False)),
        'risk_score': int(risk_assessment.get('score', 0)),
        'risk_level': risk_assessment.get('risk_level'),
        'agent_id': action_context.get('agent_id'),
        'policy_id': str(policy.id),
        'policy_name': policy.name,
        'policy_effect': policy.effect.value,
    }
    return snapshot


def _fingerprint(snapshot: dict) -> str:
    serialized = json.dumps(snapshot, sort_keys=True, separators=(',', ':'))
    return sha256(serialized.encode('utf-8')).hexdigest()


def create_approval_request(
    db: Session,
    *,
    organization_id: UUID,
    agent_id: UUID,
    policy_id: UUID,
    requested_by_user_id: UUID | None,
    action_context: dict,
    risk_assessment: dict,
) -> ApprovalRequest:
    policy = db.get(Policy, policy_id)
    if policy is None or policy.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Policy not found.')

    snapshot = _normalize_snapshot(action_context, risk_assessment, policy)
    fingerprint = _fingerprint(snapshot)

    existing = db.execute(
        select(ApprovalRequest)
        .where(
            ApprovalRequest.organization_id == organization_id,
            ApprovalRequest.agent_id == agent_id,
            ApprovalRequest.request_fingerprint == fingerprint,
            ApprovalRequest.status == ApprovalStatus.PENDING,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    settings = get_settings()
    approval = ApprovalRequest(
        organization_id=organization_id,
        agent_id=agent_id,
        requested_by_user_id=requested_by_user_id,
        policy_id=policy_id,
        status=ApprovalStatus.PENDING,
        risk_score=int(risk_assessment.get('score', 0)),
        risk_level=risk_assessment.get('risk_level', AgentRiskLevel.LOW),
        request_fingerprint=fingerprint,
        normalized_action_snapshot=snapshot,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.approval_request_expire_minutes),
    )
    db.add(approval)
    db.flush()
    record_audit_event(
        db,
        organization_id=organization_id,
        event_type=AuditEventType.APPROVAL_REQUESTED,
        actor_type=ActorType.USER if requested_by_user_id is not None else ActorType.SYSTEM,
        actor_user_id=requested_by_user_id,
        agent_id=agent_id,
        policy_id=policy_id,
        approval_request_id=approval.id,
        source='approvals.request',
        summary='Approval request created.',
        details={'approval_request_id': str(approval.id), 'agent_id': str(agent_id), 'policy_id': str(policy_id), 'risk_score': int(risk_assessment.get('score', 0)), 'risk_level': str(risk_assessment.get('risk_level', AgentRiskLevel.LOW))},
    )
    db.commit()
    db.refresh(approval)
    return approval


def list_approvals(
    db: Session,
    *,
    organization_id: UUID,
    offset: int,
    limit: int,
    status: ApprovalStatus | None = None,
) -> tuple[list[ApprovalRequest], int]:
    return list_approvals_for_org(
        db,
        organization_id=organization_id,
        offset=offset,
        limit=limit,
        status=status,
    )


def get_approval(db: Session, *, organization_id: UUID, approval_id: UUID) -> ApprovalRequest | None:
    return get_approval_by_id_for_org(db, approval_id=approval_id, organization_id=organization_id)


def resolve_approval(
    db: Session,
    *,
    organization_id: UUID,
    approval_id: UUID,
    reviewer: User,
    action: str,
    resolution_reason: str | None,
) -> ApprovalRequest:
    approval = db.execute(
        select(ApprovalRequest)
        .where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.organization_id == organization_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Approval request not found.')
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Approval request is not pending.')
    if approval.expires_at <= datetime.now(timezone.utc):
        approval.status = ApprovalStatus.EXPIRED
        approval.resolved_at = datetime.now(timezone.utc)
        approval.resolved_by_user_id = reviewer.id
        approval.resolution_reason = 'Approval expired.'
        db.flush()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Approval request has expired.')

    if action == 'approve':
        approval.status = ApprovalStatus.APPROVED
        approval.resolution_reason = resolution_reason or 'Approved by reviewer.'
    elif action == 'reject':
        approval.status = ApprovalStatus.REJECTED
        approval.resolution_reason = resolution_reason or 'Rejected by reviewer.'
    else:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail='Unsupported resolution action.')

    approval.resolved_at = datetime.now(timezone.utc)
    approval.resolved_by_user_id = reviewer.id
    db.flush()
    event_type = AuditEventType.APPROVAL_APPROVED if action == 'approve' else AuditEventType.APPROVAL_REJECTED
    record_audit_event(
        db,
        organization_id=organization_id,
        event_type=event_type,
        actor_type=ActorType.USER,
        actor_user_id=reviewer.id,
        agent_id=approval.agent_id,
        policy_id=approval.policy_id,
        approval_request_id=approval.id,
        source='approvals.resolve',
        summary='Approval request resolved.',
        details={'approval_request_id': str(approval.id), 'status': approval.status.value, 'reviewer_user_id': str(reviewer.id), 'risk_score': approval.risk_score, 'risk_level': approval.risk_level.value},
    )
    db.commit()
    db.refresh(approval)
    return approval


def approve_approval_request(db: Session, *, organization_id: UUID, approval_id: UUID, reviewer: User, resolution_reason: str | None) -> ApprovalRequest:
    return resolve_approval(
        db,
        organization_id=organization_id,
        approval_id=approval_id,
        reviewer=reviewer,
        action='approve',
        resolution_reason=resolution_reason,
    )


def reject_approval_request(db: Session, *, organization_id: UUID, approval_id: UUID, reviewer: User, resolution_reason: str | None) -> ApprovalRequest:
    return resolve_approval(
        db,
        organization_id=organization_id,
        approval_id=approval_id,
        reviewer=reviewer,
        action='reject',
        resolution_reason=resolution_reason,
    )
