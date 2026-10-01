from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, require_roles
from app.database.session import get_db
from app.models import User
from app.models.enums import ActorType, AgentRiskLevel, AgentStatus, AgentType, AuditEventType, PolicyEffect, UserRole
from app.services.audit import record_audit_event
from app.policies.engine import evaluate_policy
from app.repositories.agents import get_agent_by_id_for_org
from app.schemas.agent import AgentCreate, AgentListResponse, AgentRead, AgentUpdate
from app.schemas.policy import AuthorizationDecisionResponse
from app.schemas.risk import RiskAssessmentResponse, RiskEvaluationRequest
from app.services.agents import create_agent, disable_agent, list_agents, update_agent
from app.services.approvals import create_approval_request
from app.services.policies import list_enabled_policies_for_org
from app.services.risk import evaluate_risk

router = APIRouter(prefix='/agents', tags=['agents'])
MANAGEMENT_ROLES = (UserRole.OWNER, UserRole.ADMIN, UserRole.SECURITY_ANALYST)


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Agent not found.')


@router.post('', response_model=AgentRead, status_code=status.HTTP_201_CREATED)
def create_agent_endpoint(
    request: AgentCreate,
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
) -> AgentRead:
    return create_agent(db, organization_id=current_user.organization_id, data=request, actor_user_id=current_user.id)


@router.get('', response_model=AgentListResponse)
def list_agents_endpoint(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    agent_status: AgentStatus | None = Query(default=None, alias='status'),
    agent_type: AgentType | None = None,
    risk_level: AgentRiskLevel | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> AgentListResponse:
    agents, total = list_agents(
        db,
        organization_id=current_user.organization_id,
        offset=offset,
        limit=limit,
        status=agent_status,
        agent_type=agent_type,
        risk_level=risk_level,
    )
    return AgentListResponse(items=agents, total=total, offset=offset, limit=limit)


@router.get('/{agent_id}', response_model=AgentRead)
def get_agent_endpoint(
    agent_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> AgentRead:
    agent = get_agent_by_id_for_org(db, agent_id=agent_id, organization_id=current_user.organization_id)
    if agent is None:
        raise _not_found()
    return agent


@router.patch('/{agent_id}', response_model=AgentRead)
def update_agent_endpoint(
    agent_id: UUID,
    request: AgentUpdate,
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
) -> AgentRead:
    agent = update_agent(
        db,
        organization_id=current_user.organization_id,
        agent_id=agent_id,
        data=request,
        actor_user_id=current_user.id,
    )
    if agent is None:
        raise _not_found()
    return agent


@router.post('/{agent_id}/disable', response_model=AgentRead)
def disable_agent_endpoint(
    agent_id: UUID,
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
) -> AgentRead:
    agent = disable_agent(db, organization_id=current_user.organization_id, agent_id=agent_id, actor_user_id=current_user.id)
    if agent is None:
        raise _not_found()
    return agent


@router.post('/{agent_id}/risk/evaluate', response_model=RiskAssessmentResponse)
def evaluate_agent_risk_endpoint(
    agent_id: UUID,
    request: RiskEvaluationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> RiskAssessmentResponse:
    agent = get_agent_by_id_for_org(db, agent_id=agent_id, organization_id=current_user.organization_id)
    if agent is None:
        raise _not_found()
    risk_assessment = evaluate_risk(request, agent_id=agent.id)
    correlation_id = str(uuid4())
    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        event_type=AuditEventType.RISK_EVALUATED,
        actor_type=ActorType.USER,
        actor_user_id=current_user.id,
        agent_id=agent.id,
        correlation_id=correlation_id,
        source='agents.risk.evaluate',
        summary='Risk evaluation recorded.',
        details={'agent_id': str(agent.id), 'action_type': request.action_type.value, 'environment': request.environment.value, 'risk_score': risk_assessment.score, 'risk_level': risk_assessment.risk_level.value},
    )
    db.commit()
    return risk_assessment


@router.post('/{agent_id}/authorize', response_model=AuthorizationDecisionResponse)
def authorize_agent_action_endpoint(
    agent_id: UUID,
    request: RiskEvaluationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> AuthorizationDecisionResponse:
    agent = get_agent_by_id_for_org(db, agent_id=agent_id, organization_id=current_user.organization_id)
    if agent is None:
        raise _not_found()

    correlation_id = str(uuid4())
    risk_assessment = evaluate_risk(request, agent_id=agent.id)
    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        event_type=AuditEventType.RISK_EVALUATED,
        actor_type=ActorType.USER,
        actor_user_id=current_user.id,
        agent_id=agent.id,
        correlation_id=correlation_id,
        source='agents.authorize.risk',
        summary='Risk evaluation recorded for authorization decision.',
        details={'agent_id': str(agent.id), 'action_type': request.action_type.value, 'environment': request.environment.value, 'risk_score': risk_assessment.score, 'risk_level': risk_assessment.risk_level.value},
    )
    policies = list_enabled_policies_for_org(db, organization_id=current_user.organization_id)
    decision = evaluate_policy(request.model_dump(mode='json'), risk_assessment.model_dump(mode='json'), policies)

    matched_policy = None
    approval_request_id = None
    if decision.matched_policy_id is not None:
        matched_policy = next((p for p in policies if p.id == decision.matched_policy_id), None)
        if matched_policy is not None:
            matched_policy = {
                'id': str(matched_policy.id),
                'name': matched_policy.name,
                'effect': matched_policy.effect.value,
                'priority': matched_policy.priority,
            }

    if decision.decision == PolicyEffect.REQUIRE_APPROVAL and decision.matched_policy_id is not None:
        approval = create_approval_request(
            db,
            organization_id=current_user.organization_id,
            agent_id=agent.id,
            policy_id=decision.matched_policy_id,
            requested_by_user_id=current_user.id,
            action_context={
                'agent_id': str(agent.id),
                'agent_type': agent.agent_type.value,
                **request.model_dump(mode='json', exclude_none=True),
            },
            risk_assessment=risk_assessment.model_dump(mode='json'),
        )
        approval_request_id = approval.id

    record_audit_event(
        db,
        organization_id=current_user.organization_id,
        event_type=AuditEventType.AUTHORIZATION_EVALUATED,
        actor_type=ActorType.USER,
        actor_user_id=current_user.id,
        agent_id=agent.id,
        policy_id=decision.matched_policy_id,
        correlation_id=correlation_id,
        source='agents.authorize',
        summary='Authorization decision evaluated.',
        details={'agent_id': str(agent.id), 'decision': decision.decision.value, 'risk_score': decision.risk_score, 'risk_level': (decision.risk_level or risk_assessment.risk_level.value), 'matched_policy_id': str(decision.matched_policy_id) if decision.matched_policy_id else None},
    )
    db.commit()

    return AuthorizationDecisionResponse(
        decision=decision.decision,
        risk={
            'score': risk_assessment.score,
            'risk_level': risk_assessment.risk_level.value,
            'factors': risk_assessment.factors,
        },
        matched_policy=matched_policy,
        reason=decision.reason,
        approval_request_id=approval_request_id,
    )