from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Agent
from app.models.enums import AgentRiskLevel, AgentStatus, AgentType
from app.repositories.agents import (
    create_agent as repository_create_agent,
    get_agent_by_id_for_org,
    list_agents_for_org,
    update_agent_for_org,
)
from app.schemas.agent import AgentCreate, AgentUpdate


def create_agent(db: Session, *, organization_id: UUID, data: AgentCreate) -> Agent:
    agent = repository_create_agent(
        db,
        organization_id=organization_id,
        name=data.name,
        description=data.description,
        agent_type=data.agent_type,
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


def update_agent(db: Session, *, organization_id: UUID, agent_id: UUID, data: AgentUpdate) -> Agent | None:
    agent = update_agent_for_org(
        db,
        agent_id=agent_id,
        organization_id=organization_id,
        updates=data.model_dump(exclude_unset=True),
    )
    if agent is None:
        return None
    db.commit()
    db.refresh(agent)
    return agent


def disable_agent(db: Session, *, organization_id: UUID, agent_id: UUID) -> Agent | None:
    return update_agent(
        db,
        organization_id=organization_id,
        agent_id=agent_id,
        data=AgentUpdate(status=AgentStatus.DISABLED),
    )