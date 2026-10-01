from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Agent
from app.models.enums import ActorType, AgentRiskLevel, AgentStatus, AgentType, AuditEventType
from app.services.audit import record_audit_event
from app.repositories.agents import (
    create_agent as repository_create_agent,
    get_agent_by_id_for_org,
    list_agents_for_org,
    update_agent_for_org,
)
from app.schemas.agent import AgentCreate, AgentUpdate


def create_agent(db: Session, *, organization_id: UUID, data: AgentCreate, actor_user_id: UUID | None = None) -> Agent:
    agent = repository_create_agent(
        db,
        organization_id=organization_id,
        name=data.name,
        description=data.description,
        agent_type=data.agent_type,
    )
    db.flush()
    record_audit_event(
        db,
        organization_id=organization_id,
        event_type=AuditEventType.AGENT_CREATED,
        actor_type=ActorType.USER if actor_user_id is not None else ActorType.SYSTEM,
        actor_user_id=actor_user_id,
        agent_id=agent.id,
        source='agents.create',
        summary='Agent created.',
        details={'agent_id': str(agent.id), 'agent_name': agent.name, 'agent_type': agent.agent_type.value},
    )
    db.commit()
    db.refresh(agent)
    return agent


def list_agents(
    db: Session,
    *,
    organization_id: UUID,
    offset: int,
    limit: int,
    status: AgentStatus | None,
    agent_type: AgentType | None,
    risk_level: AgentRiskLevel | None,
) -> tuple[list[Agent], int]:
    return list_agents_for_org(
        db,
        organization_id=organization_id,
        offset=offset,
        limit=limit,
        status=status,
        agent_type=agent_type,
        risk_level=risk_level,
    )


def update_agent(db: Session, *, organization_id: UUID, agent_id: UUID, data: AgentUpdate, actor_user_id: UUID | None = None) -> Agent | None:
    agent = update_agent_for_org(
        db,
        agent_id=agent_id,
        organization_id=organization_id,
        updates=data.model_dump(exclude_unset=True),
    )
    if agent is None:
        return None
    event_type = AuditEventType.AGENT_DISABLED if getattr(agent, 'status', None) == AgentStatus.DISABLED else AuditEventType.AGENT_UPDATED
    record_audit_event(
        db,
        organization_id=organization_id,
        event_type=event_type,
        actor_type=ActorType.USER if actor_user_id is not None else ActorType.SYSTEM,
        actor_user_id=actor_user_id,
        agent_id=agent.id,
        source='agents.update',
        summary='Agent updated.' if event_type != AuditEventType.AGENT_DISABLED else 'Agent disabled.',
        details={'agent_id': str(agent.id), 'agent_name': agent.name, 'status': agent.status.value if hasattr(agent.status, 'value') else str(agent.status)},
    )
    db.commit()
    db.refresh(agent)
    return agent


def disable_agent(db: Session, *, organization_id: UUID, agent_id: UUID, actor_user_id: UUID | None = None) -> Agent | None:
    return update_agent(
        db,
        organization_id=organization_id,
        agent_id=agent_id,
        data=AgentUpdate(status=AgentStatus.DISABLED),
        actor_user_id=actor_user_id,
    )