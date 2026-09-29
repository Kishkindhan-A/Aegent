from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, require_roles
from app.database.session import get_db
from app.models import User
from app.models.enums import AgentRiskLevel, AgentStatus, AgentType, UserRole
from app.repositories.agents import get_agent_by_id_for_org
from app.schemas.agent import AgentCreate, AgentListResponse, AgentRead, AgentUpdate
from app.schemas.risk import RiskAssessmentResponse, RiskEvaluationRequest
from app.services.agents import create_agent, disable_agent, list_agents, update_agent
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
    return create_agent(db, organization_id=current_user.organization_id, data=request)


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
    agent = disable_agent(db, organization_id=current_user.organization_id, agent_id=agent_id)
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
    return evaluate_risk(request, agent_id=agent.id)