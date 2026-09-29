from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import AgentRiskLevel, AgentStatus, AgentType


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (
        Index("ix_agents_organization_status", "organization_id", "status"),
        Index("ix_agents_organization_agent_type", "organization_id", "agent_type"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_type: Mapped[AgentType] = mapped_column(
        Enum(AgentType, name="agent_type", native_enum=True, validate_strings=True),
        nullable=False,
        default=AgentType.GENERAL,
        server_default="GENERAL",
    )
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus, name="agent_status", native_enum=True, validate_strings=True),
        nullable=False,
        default=AgentStatus.ACTIVE,
        server_default="ACTIVE",
    )
    risk_level: Mapped[AgentRiskLevel] = mapped_column(
        Enum(AgentRiskLevel, name="agent_risk_level", native_enum=True, validate_strings=True),
        nullable=False,
        default=AgentRiskLevel.LOW,
        server_default="LOW",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    organization: Mapped["Organization"] = relationship(back_populates="agents")
    approval_requests: Mapped[list["ApprovalRequest"]] = relationship(back_populates="agent")