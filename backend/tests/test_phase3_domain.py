from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database.base import Base
from app.database.session import SessionLocal
from app.models import Organization, User
from app.models.enums import OrganizationStatus, UserRole, UserStatus
from app.schemas.organization import OrganizationCreate
from app.schemas.user import UserCreate, UserRead


@pytest.fixture
def session():
    session = SessionLocal()
    transaction = session.begin()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_organization_creation(session):
    org = Organization(name='Acme Security', slug=f'acme-{uuid4().hex[:8]}')
    session.add(org)
    session.flush()

    assert isinstance(org.id, UUID)
    assert org.status is OrganizationStatus.ACTIVE
    assert org.created_at is not None
    assert org.updated_at is not None


def test_unique_organization_slug(session):
    slug = f'org-{uuid4().hex[:8]}'
    session.add(Organization(name='First Org', slug=slug))
    session.flush()

    with pytest.raises(IntegrityError):
        session.add(Organization(name='Second Org', slug=slug))
        session.flush()


def test_user_creation_and_relationship(session):
    org = Organization(name='Tenant A', slug=f'tenant-a-{uuid4().hex[:8]}')
    session.add(org)
    session.flush()

    user = User(
        organization_id=org.id,
        email=f'user-{uuid4().hex[:8]}@example.com',
        password_hash='hashed_value_123',
        full_name='Example User',
        role=UserRole.OWNER,
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    session.flush()

    assert isinstance(user.id, UUID)
    assert user.organization_id == org.id
    assert user.organization is org
    assert org.users[0].id == user.id


def test_user_role_and_status_values():
    assert list(UserRole) == [
        UserRole.OWNER,
        UserRole.ADMIN,
        UserRole.SECURITY_ANALYST,
        UserRole.MEMBER,
    ]
    assert list(UserStatus) == [
        UserStatus.ACTIVE,
        UserStatus.INVITED,
        UserStatus.SUSPENDED,
        UserStatus.DISABLED,
    ]


def test_same_email_allowed_in_different_organizations(session):
    email = f'person-{uuid4().hex[:8]}@example.com'
    org_a = Organization(name='Org A', slug=f'org-a-{uuid4().hex[:8]}')
    org_b = Organization(name='Org B', slug=f'org-b-{uuid4().hex[:8]}')
    session.add_all([org_a, org_b])
    session.flush()

    session.add_all(
        [
            User(
                organization_id=org_a.id,
                email=email,
                password_hash='hash-a',
                full_name='User A',
                role=UserRole.MEMBER,
                status=UserStatus.ACTIVE,
            ),
            User(
                organization_id=org_b.id,
                email=email,
                password_hash='hash-b',
                full_name='User B',
                role=UserRole.MEMBER,
                status=UserStatus.ACTIVE,
            ),
        ]
    )
    session.flush()

    results = session.execute(
        select(User).where(User.email == email).order_by(User.organization_id)
    ).scalars().all()
    assert len(results) == 2
    assert {result.organization_id for result in results} == {org_a.id, org_b.id}


def test_user_unique_org_email_constraint(session):
    org = Organization(name='Shared Org', slug=f'shared-{uuid4().hex[:8]}')
    session.add(org)
    session.flush()

    first = User(
        organization_id=org.id,
        email=f'duplicate-{uuid4().hex[:8]}@example.com',
        password_hash='hash-one',
        full_name='First',
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    second = User(
        organization_id=org.id,
        email=first.email,
        password_hash='hash-two',
        full_name='Second',
        role=UserRole.MEMBER,
        status=UserStatus.ACTIVE,
    )
    session.add_all([first, second])
    with pytest.raises(IntegrityError):
        session.flush()


def test_foreign_key_behavior(session):
    user = User(
        organization_id=uuid4(),
        email=f'foreign-{uuid4().hex[:8]}@example.com',
        password_hash='hash',
        full_name='Unknown Org User',
        role=UserRole.MEMBER,
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    with pytest.raises(IntegrityError):
        session.flush()


def test_timestamps_are_timezone_aware(session):
    org = Organization(name='Time Org', slug=f'time-{uuid4().hex[:8]}')
    session.add(org)
    session.flush()

    assert isinstance(org.created_at, datetime)
    assert org.created_at.tzinfo is not None
    assert isinstance(org.updated_at, datetime)
    assert org.updated_at.tzinfo is not None


def test_schema_validation_and_enum_rejection():
    with pytest.raises(ValidationError):
        OrganizationCreate(name='', slug='')

    with pytest.raises(ValidationError):
        OrganizationCreate(name='Bad Org', slug='bad-slug', status='INVALID_STATUS')

    with pytest.raises(ValidationError):
        UserCreate(
            organization_id=uuid4(),
            email='not-an-email',
            password_hash='hash',
            full_name='User',
            role='bad-role',
            status='bad-status',
        )


def test_password_hash_not_exposed_in_read_schema(session):
    org = Organization(name='Read Org', slug=f'read-{uuid4().hex[:8]}')
    session.add(org)
    session.flush()

    user = User(
        organization_id=org.id,
        email=f'read-{uuid4().hex[:8]}@example.com',
        password_hash='secret-hash',
        full_name='Read User',
        role=UserRole.SECURITY_ANALYST,
        status=UserStatus.INVITED,
    )
    session.add(user)
    session.flush()

    read_model = UserRead.model_validate(user)
    data = read_model.model_dump()

    assert 'password_hash' not in UserRead.model_fields
    assert 'password_hash' not in data
    assert data['email'] == user.email
    assert data['organization_id'] == org.id


def test_model_registration_in_metadata():
    table_names = set(Base.metadata.tables.keys())
    assert 'organizations' in table_names
    assert 'users' in table_names


def test_organization_and_user_models_are_importable():
    assert Organization is not None
    assert User is not None
