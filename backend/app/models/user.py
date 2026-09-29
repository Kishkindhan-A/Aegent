from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import UserRole, UserStatus


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_users_organization_email"),
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
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=True, validate_strings=True),
        nullable=False,
        default=UserRole.MEMBER,
        server_default="MEMBER",
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status", native_enum=True, validate_strings=True),
        nullable=False,
        default=UserStatus.ACTIVE,
        server_default="ACTIVE",
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

    organization: Mapped["Organization"] = relationship(back_populates="users")
    policies: Mapped[list["Policy"]] = relationship(back_populates="created_by_user")
    approval_requests_requested: Mapped[list["ApprovalRequest"]] = relationship(
        back_populates="requested_by_user",
        foreign_keys='[ApprovalRequest.requested_by_user_id]',
    )
    approval_requests_resolved: Mapped[list["ApprovalRequest"]] = relationship(
        back_populates="resolved_by_user",
        foreign_keys='[ApprovalRequest.resolved_by_user_id]',
    )
