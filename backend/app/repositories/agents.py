from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Agent
from app.models.enums import AgentRiskLevel, AgentStatus, AgentType


def create_agent(
    db: Session,
    *,
    organization_id: UUID,
    name: str,
    description: str | None,
    agent_type: AgentType,
) -> Agent:
    agent = Agent(
        organization_id=organization_id,
        name=name,
        description=description,
        agent_type=agent_type,
    )
    db.add(agent)
    db.flush()
    return agent


def get_agent_by_id_for_org(db: Session, *, agent_id: UUID, organization_id: UUID) -> Agent | None:
    return db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.organization_id == organization_id,
        )
    ).scalar_one_or_none()


def list_agents_for_org(
    db: Session,
    *,
    organization_id: UUID,
    offset: int,
    limit: int,
    status: AgentStatus | None = None,
    agent_type: AgentType | None = None,
    risk_level: AgentRiskLevel | None = None,
) -> tuple[list[Agent], int]:
    filters = [Agent.organization_id == organization_id]
    if status is not None:
        filters.append(Agent.status == status)
    if agent_type is not None:
        filters.append(Agent.agent_type == agent_type)
    if risk_level is not None:
        filters.append(Agent.risk_level == risk_level)

    total = db.scalar(select(func.count(Agent.id)).where(*filters)) or 0
    agents = db.execute(
        select(Agent)
        .where(*filters)
        .order_by(Agent.created_at.desc(), Agent.id)
        .offset(offset)
        .limit(limit)
    ).scalars().all()
    return agents, total


def update_agent_for_org(
    db: Session,
    *,
    agent_id: UUID,
    organization_id: UUID,
    updates: dict[str, object],
) -> Agent | None:
    agent = get_agent_by_id_for_org(db, agent_id=agent_id, organization_id=organization_id)
    if agent is None:
        return None
    for field, value in updates.items():
        setattr(agent, field, value)
    db.flush()
    return agent