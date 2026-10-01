from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.database.session import SessionLocal
from app.main import app
from app.models import Agent, ApprovalRequest, AuditEvent, Organization, Policy, User
from app.models.enums import ActionType, ApprovalStatus, DataSensitivity, Environment, PolicyEffect, PrivilegeLevel, UserRole
from app.policies.engine import evaluate_policy
from app.security.passwords import hash_password

client = TestClient(app)
_created_organization_ids: set[UUID] = set()


@pytest.fixture(autouse=True)
def clean_phase7_test_data():
    yield
    if not _created_organization_ids:
        return
    with SessionLocal() as session:
        session.execute(delete(AuditEvent).where(AuditEvent.organization_id.in_(_created_organization_ids)))
        session.execute(delete(ApprovalRequest).where(ApprovalRequest.organization_id.in_(_created_organization_ids)))
        session.execute(delete(Policy).where(Policy.organization_id.in_(_created_organization_ids)))
        session.execute(delete(Agent).where(Agent.organization_id.in_(_created_organization_ids)))
        session.execute(delete(User).where(User.organization_id.in_(_created_organization_ids)))
        session.execute(delete(Organization).where(Organization.id.in_(_created_organization_ids)))
        session.commit()
    _created_organization_ids.clear()


def _create_organization(name: str) -> Organization:
    with SessionLocal() as session:
        organization = Organization(name=name, slug=f'{name.lower().replace(" ", "-")}-{uuid4().hex[:8]}')
        session.add(organization)
        session.flush()
        _created_organization_ids.add(organization.id)
        session.commit()
        session.refresh(organization)
        return organization


def _create_user(organization: Organization, email: str, role: UserRole = UserRole.MEMBER) -> User:
    with SessionLocal() as session:
        user = User(
            organization_id=organization.id,
            email=email.lower(),
            password_hash=hash_password('StrongPass!123'),
            full_name='Phase 7 User',
            role=role,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def _login(user: User, organization: Organization):
    response = client.post(
        '/api/v1/auth/login',
        json={'email': user.email, 'password': 'StrongPass!123', 'organization_id': str(organization.id)},
    )
    assert response.status_code == 200, response.text
    return response.json()['access_token']


def _create_agent(organization: Organization, name: str) -> Agent:
    with SessionLocal() as session:
        agent = Agent(organization_id=organization.id, name=name)
        session.add(agent)
        session.commit()
        session.refresh(agent)
        return agent


def _create_policy(organization: Organization, *, name: str, effect: PolicyEffect, priority: int, conditions: dict | None = None, enabled: bool = True):
    with SessionLocal() as session:
        policy = Policy(
            organization_id=organization.id,
            name=name,
            description=name,
            effect=effect,
            priority=priority,
            enabled=enabled,
            conditions=conditions or {},
            created_by_user_id=None,
        )
        session.add(policy)
        session.commit()
        session.refresh(policy)
        return policy


def test_policy_priority_and_default_deny_are_deterministic():
    organization = _create_organization('OrgAlpha')
    allow_policy = _create_policy(
        organization,
        name='allow-read',
        effect=PolicyEffect.ALLOW,
        priority=10,
        conditions={'action_type': ActionType.READ.value, 'environment': Environment.PRODUCTION.value},
    )
    deny_policy = _create_policy(
        organization,
        name='deny-read',
        effect=PolicyEffect.DENY,
        priority=100,
        conditions={'action_type': ActionType.READ.value},
    )
    policy_decision = evaluate_policy(
        {
            'agent_id': str(uuid4()),
            'action_type': ActionType.READ.value,
            'environment': Environment.PRODUCTION.value,
            'data_sensitivity': DataSensitivity.CONFIDENTIAL.value,
            'privilege_level': PrivilegeLevel.STANDARD.value,
            'external_network_access': False,
            'destructive_capability': False,
            'credential_access': False,
            'financial_impact': False,
        },
        {
            'score': 30,
            'risk_level': 'MEDIUM',
            'factors': [],
        },
        [allow_policy, deny_policy],
    )
    assert policy_decision.decision == PolicyEffect.DENY
    assert policy_decision.matched_policy_id == deny_policy.id
    assert policy_decision.reason == 'Matched policy: deny-read.'

    default_decision = evaluate_policy(
        {'action_type': ActionType.ADMIN.value, 'environment': Environment.PRODUCTION.value},
        {'score': 10, 'risk_level': 'LOW', 'factors': []},
        [],
    )
    assert default_decision.decision == PolicyEffect.DENY
    assert 'default deny' in default_decision.reason.lower()


def test_authorize_endpoint_evaluates_policies_and_creates_pending_approval():
    organization = _create_organization('OrgPolicy')
    owner = _create_user(organization, 'owner@aegent.example', UserRole.OWNER)
    agent = _create_agent(organization, 'policy-agent')
    token = _login(owner, organization)

    _create_policy(
        organization,
        name='require-approval-for-write',
        effect=PolicyEffect.REQUIRE_APPROVAL,
        priority=50,
        conditions={'action_type': ActionType.WRITE.value, 'environment': Environment.PRODUCTION.value},
    )

    response = client.post(
        f'/api/v1/agents/{agent.id}/authorize',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'action_type': 'WRITE',
            'resource_type': 'DATABASE',
            'operation': 'UPDATE_CONTRACT',
            'environment': 'PRODUCTION',
            'data_sensitivity': 'CONFIDENTIAL',
            'privilege_level': 'STANDARD',
            'external_network_access': False,
            'write_capability': True,
            'destructive_capability': False,
            'credential_access': False,
            'financial_impact': False,
            'requires_human_approval': False,
            'metadata': {},
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload['decision'] == 'REQUIRE_APPROVAL'
    assert payload['approval_request_id'] is not None

    with SessionLocal() as session:
        approval = session.query(ApprovalRequest).filter_by(id=payload['approval_request_id']).one()
        assert approval.status == ApprovalStatus.PENDING
        assert approval.organization_id == organization.id
        assert approval.agent_id == agent.id


def test_cross_tenant_policy_and_approval_are_restricted():
    org_a = _create_organization('OrgA')
    org_b = _create_organization('OrgB')
    user_a = _create_user(org_a, 'usera@aegent.example', UserRole.OWNER)
    user_b = _create_user(org_b, 'userb@aegent.example', UserRole.OWNER)
    agent_a = _create_agent(org_a, 'agent-a')
    agent_b = _create_agent(org_b, 'agent-b')
    token_a = _login(user_a, org_a)
    token_b = _login(user_b, org_b)

    _create_policy(
        org_b,
        name='org-b-policy',
        effect=PolicyEffect.ALLOW,
        priority=10,
        conditions={'action_type': ActionType.READ.value},
    )

    response = client.get(
        '/api/v1/policies',
        headers={'Authorization': f'Bearer {token_a}'},
    )
    assert response.status_code == 200
    policy_ids = {item['id'] for item in response.json()['items']}
    assert all(str(policy.id) not in policy_ids for policy in [
        _create_policy(org_b, name='shadow-policy', effect=PolicyEffect.DENY, priority=20, conditions={'action_type': ActionType.READ.value})
    ])

    response = client.post(
        f'/api/v1/agents/{agent_a.id}/authorize',
        headers={'Authorization': f'Bearer {token_b}'},
        json={
            'action_type': 'READ',
            'resource_type': 'DOCS',
            'operation': 'VIEW',
            'environment': 'PRODUCTION',
            'data_sensitivity': 'PUBLIC',
            'privilege_level': 'LOW',
            'external_network_access': False,
            'write_capability': False,
            'destructive_capability': False,
            'credential_access': False,
            'financial_impact': False,
            'requires_human_approval': False,
            'metadata': {},
        },
    )
    assert response.status_code == 404
