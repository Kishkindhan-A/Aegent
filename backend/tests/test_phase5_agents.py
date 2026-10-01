from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import delete

from app.database.session import SessionLocal
from app.main import app
from app.models import Agent, AuditEvent, Organization, User
from app.models.enums import AgentRiskLevel, AgentStatus, AgentType, UserRole
from app.schemas.agent import AgentCreate, AgentUpdate
from app.security.passwords import hash_password

client = TestClient(app)
_created_organization_ids: set[UUID] = set()


@pytest.fixture(autouse=True)
def clean_phase5_test_data():
    yield
    if not _created_organization_ids:
        return
    with SessionLocal() as session:
        session.execute(delete(AuditEvent).where(AuditEvent.organization_id.in_(_created_organization_ids)))
        session.execute(delete(Agent).where(Agent.organization_id.in_(_created_organization_ids)))
        session.execute(delete(User).where(User.organization_id.in_(_created_organization_ids)))
        session.execute(delete(Organization).where(Organization.id.in_(_created_organization_ids)))
        session.commit()
    _created_organization_ids.clear()


def _create_user(email: str, role: UserRole, org_name: str) -> tuple[Organization, User]:
    with SessionLocal() as session:
        organization = Organization(name=org_name, slug=f'{org_name.lower().replace(" ", "-")}-{uuid4().hex[:8]}')
        session.add(organization)
        session.flush()
        _created_organization_ids.add(organization.id)
        user = User(
            organization_id=organization.id,
            email=email,
            password_hash=hash_password('StrongPass!123'),
            full_name='Phase 5 User',
            role=role,
        )
        session.add(user)
        session.commit()
        session.refresh(organization)
        session.refresh(user)
        return organization, user


def _token(user: User, organization: Organization) -> str:
    response = client.post(
        '/api/v1/auth/login',
        json={
            'email': user.email,
            'password': 'StrongPass!123',
            'organization_id': str(organization.id),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()['access_token']


def _create_agent(organization_id: UUID, name: str) -> Agent:
    with SessionLocal() as session:
        agent = Agent(organization_id=organization_id, name=name)
        session.add(agent)
        session.commit()
        session.refresh(agent)
        return agent


def test_agent_model_defaults_and_relationship():
    organization, _ = _create_user(
        f'model-{uuid4().hex[:8]}@example.com', UserRole.OWNER, 'Model Org'
    )
    with SessionLocal() as session:
        agent = Agent(organization_id=organization.id, name='Model Agent')
        session.add(agent)
        session.flush()

        assert isinstance(agent.id, UUID)
        assert agent.status is AgentStatus.ACTIVE
        assert agent.risk_level is AgentRiskLevel.LOW
        assert agent.agent_type is AgentType.GENERAL
        assert isinstance(agent.created_at, datetime)
        assert agent.created_at.tzinfo is not None
        assert agent.organization.id == organization.id


def test_agent_schemas_reject_invalid_enums_and_do_not_accept_ownership_field():
    valid = AgentCreate(name='Schema Agent', agent_type=AgentType.CODING)
    assert valid.agent_type is AgentType.CODING
    assert 'organization_id' not in AgentCreate.model_fields

    with pytest.raises(ValidationError):
        AgentCreate(name='Bad Agent', agent_type='NOT_A_TYPE')
    with pytest.raises(ValidationError):
        AgentUpdate(status='NOT_A_STATUS')


def test_create_is_tenant_bound_and_restricted_to_management_roles():
    org_a, owner_a = _create_user(f'owner-{uuid4().hex[:8]}@example.com', UserRole.OWNER, 'Create A')
    org_b, _ = _create_user(f'member-{uuid4().hex[:8]}@example.com', UserRole.MEMBER, 'Create B')
    owner_token = _token(owner_a, org_a)

    response = client.post(
        '/api/v1/agents',
        headers={'Authorization': f'Bearer {owner_token}'},
        json={'name': 'Owned Agent', 'organization_id': str(org_b.id)},
    )
    assert response.status_code == 201, response.text
    assert response.json()['organization_id'] == str(org_a.id)

    member_org, member = _create_user(f'member2-{uuid4().hex[:8]}@example.com', UserRole.MEMBER, 'Member Org')
    member_token = _token(member, member_org)
    forbidden = client.post(
        '/api/v1/agents',
        headers={'Authorization': f'Bearer {member_token}'},
        json={'name': 'Forbidden Agent'},
    )
    assert forbidden.status_code == 403


def test_list_get_update_and_disable_never_cross_tenant():
    org_a, user_a = _create_user(f'a-{uuid4().hex[:8]}@example.com', UserRole.ADMIN, 'Tenant A')
    org_b, user_b = _create_user(f'b-{uuid4().hex[:8]}@example.com', UserRole.ADMIN, 'Tenant B')
    agent_a = _create_agent(org_a.id, 'Agent A')
    agent_b = _create_agent(org_b.id, 'Agent B')
    token_a = _token(user_a, org_a)
    headers = {'Authorization': f'Bearer {token_a}'}

    listing = client.get('/api/v1/agents', headers=headers)
    assert listing.status_code == 200
    assert [item['id'] for item in listing.json()['items']] == [str(agent_a.id)]

    own = client.get(f'/api/v1/agents/{agent_a.id}', headers=headers)
    assert own.status_code == 200
    foreign = client.get(f'/api/v1/agents/{agent_b.id}', headers=headers)
    assert foreign.status_code == 404

    moved = client.patch(
        f'/api/v1/agents/{agent_b.id}',
        headers=headers,
        json={'name': 'Hijacked Agent', 'organization_id': str(org_a.id)},
    )
    assert moved.status_code == 404
    disabled = client.post(f'/api/v1/agents/{agent_b.id}/disable', headers=headers)
    assert disabled.status_code == 404

    updated = client.patch(
        f'/api/v1/agents/{agent_a.id}',
        headers=headers,
        json={'name': 'Updated Agent', 'status': 'SUSPENDED'},
    )
    assert updated.status_code == 200
    assert updated.json()['status'] == 'SUSPENDED'

    disabled = client.post(f'/api/v1/agents/{agent_a.id}/disable', headers=headers)
    assert disabled.status_code == 200
    assert disabled.json()['status'] == 'DISABLED'


def test_list_filters_and_pagination():
    organization, user = _create_user(f'filter-{uuid4().hex[:8]}@example.com', UserRole.SECURITY_ANALYST, 'Filter Org')
    _create_agent(organization.id, 'First Filter Agent')
    _create_agent(organization.id, 'Second Filter Agent')
    token = _token(user, organization)

    response = client.get('/api/v1/agents?offset=1&limit=1', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    payload = response.json()
    assert payload['total'] == 2
    assert payload['offset'] == 1
    assert payload['limit'] == 1
    assert len(payload['items']) == 1

    filtered = client.get('/api/v1/agents?agent_type=CODING', headers={'Authorization': f'Bearer {token}'})
    assert filtered.status_code == 200
    assert filtered.json()['items'] == []