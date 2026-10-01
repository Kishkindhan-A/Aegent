from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.database.session import SessionLocal
from app.main import app
from app.models import Agent, ApprovalRequest, AuditEvent, Organization, Policy, User
from app.models.enums import (
    ActionType,
    ActorType,
    AgentType,
    ApprovalStatus,
    AuditEventCategory,
    AuditEventType,
    DataSensitivity,
    Environment,
    EventSeverity,
    PolicyEffect,
    PrivilegeLevel,
    UserRole,
)
from app.security.passwords import hash_password

client = TestClient(app)
_created_organization_ids: set[str] = set()


@pytest.fixture(autouse=True)
def clean_phase8_data():
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
        _created_organization_ids.add(str(organization.id))
        session.commit()
        session.refresh(organization)
        return organization


def _create_user(organization: Organization, email: str, role: UserRole = UserRole.MEMBER) -> User:
    with SessionLocal() as session:
        user = User(
            organization_id=organization.id,
            email=email.lower(),
            password_hash=hash_password('StrongPass!123'),
            full_name='Audit User',
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
        agent = Agent(organization_id=organization.id, name=name, agent_type=AgentType.GENERAL)
        session.add(agent)
        session.commit()
        session.refresh(agent)
        return agent


def _create_policy(organization: Organization, name: str, effect: PolicyEffect, conditions: dict | None = None, enabled: bool = True) -> Policy:
    with SessionLocal() as session:
        policy = Policy(
            organization_id=organization.id,
            name=name,
            description=name,
            effect=effect,
            priority=50,
            enabled=enabled,
            conditions=conditions or {},
            created_by_user_id=None,
        )
        session.add(policy)
        session.commit()
        session.refresh(policy)
        return policy


def _create_audit_event(organization: Organization, *, event_type: AuditEventType, summary: str, details: dict | None = None, actor_user_id: str | None = None, agent_id: str | None = None, policy_id: str | None = None) -> AuditEvent:
    with SessionLocal() as session:
        event = AuditEvent(
            organization_id=organization.id,
            event_type=event_type,
            category=AuditEventCategory.AUTHENTICATION if event_type in {AuditEventType.AUTH_LOGIN_SUCCESS, AuditEventType.AUTH_LOGOUT} else AuditEventCategory.AGENT,
            severity=EventSeverity.INFO,
            actor_type=ActorType.USER,
            actor_user_id=actor_user_id,
            agent_id=agent_id,
            policy_id=policy_id,
            correlation_id=str(uuid4()),
            source='test.audit',
            summary=summary,
            details=details or {},
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return event


def test_audit_event_model_and_sanitization_round_trip():
    organization = _create_organization('AuditOrg')
    user = _create_user(organization, 'owner@audit.example', UserRole.OWNER)
    agent = _create_agent(organization, 'audit-agent')
    policy = _create_policy(organization, 'audit-policy', PolicyEffect.ALLOW, {'action_type': ActionType.READ.value})

    event = _create_audit_event(
        organization,
        event_type=AuditEventType.RISK_EVALUATED,
        summary='Risk evaluated for agent action.',
        actor_user_id=str(user.id),
        agent_id=str(agent.id),
        policy_id=str(policy.id),
        details={
            'safe': 'value',
            'nested': {
                'password': 'secret',
                'access_token': 'abc',
                'api_key': 'nope',
            },
            'risk_score': 38,
            'risk_level': 'MEDIUM',
            'resource_type': 'DATABASE',
        },
    )

    assert event.organization_id == organization.id
    assert event.event_type == AuditEventType.RISK_EVALUATED
    assert event.category == AuditEventCategory.RISK
    assert event.severity == EventSeverity.INFO
    assert event.created_at.tzinfo is not None
    assert event.details['safe'] == 'value'
    assert 'password' not in str(event.details)
    assert 'access_token' not in str(event.details)
    assert 'api_key' not in str(event.details)

    with SessionLocal() as session:
        stored = session.get(AuditEvent, event.id)
        assert stored is not None
        assert stored.summary == 'Risk evaluated for agent action.'
        assert stored.details['risk_score'] == 38


def test_audit_tenant_isolation_and_rbac():
    org_a = _create_organization('OrgA')
    org_b = _create_organization('OrgB')
    user_a = _create_user(org_a, 'usera@audit.example', UserRole.OWNER)
    user_b = _create_user(org_b, 'userb@audit.example', UserRole.ADMIN)
    token_a = _login(user_a, org_a)
    token_b = _login(user_b, org_b)

    event_a = _create_audit_event(org_a, event_type=AuditEventType.AUTH_LOGIN_SUCCESS, summary='OrgA login', actor_user_id=str(user_a.id))
    _create_audit_event(org_b, event_type=AuditEventType.AUTH_LOGIN_SUCCESS, summary='OrgB login', actor_user_id=str(user_b.id))

    response = client.get('/api/v1/audit/events', headers={'Authorization': f'Bearer {token_a}'})
    assert response.status_code == 200, response.text
    payload = response.json()
    ids = {item['id'] for item in payload['items']}
    assert str(event_a.id) in ids
    assert len(ids) == 1

    response = client.get(f'/api/v1/audit/events/{event_a.id}', headers={'Authorization': f'Bearer {token_a}'})
    assert response.status_code == 200, response.text

    response = client.get(f'/api/v1/audit/events/{_create_audit_event(org_b, event_type=AuditEventType.AUTH_LOGOUT, summary="Other org event", actor_user_id=str(user_b.id)).id}', headers={'Authorization': f'Bearer {token_a}'})
    assert response.status_code == 404

    member = _create_user(org_a, 'member@audit.example', UserRole.MEMBER)
    member_token = _login(member, org_a)
    response = client.get('/api/v1/audit/events', headers={'Authorization': f'Bearer {member_token}'})
    assert response.status_code == 403

    response = client.get('/api/v1/audit/events', headers={'Authorization': f'Bearer {token_b}'})
    assert response.status_code == 200
    assert all(item['organization_id'] == str(org_b.id) for item in response.json()['items'])


def test_audit_event_integration_for_agent_policy_and_approval_lifecycle():
    organization = _create_organization('LifecycleOrg')
    owner = _create_user(organization, 'owner@lifecycle.example', UserRole.OWNER)
    token = _login(owner, organization)
    reviewer = _create_user(organization, 'reviewer@lifecycle.example', UserRole.SECURITY_ANALYST)
    reviewer_token = _login(reviewer, organization)
    agent = _create_agent(organization, 'lifecycle-agent')
    _create_policy(
        organization,
        'approval-policy',
        PolicyEffect.REQUIRE_APPROVAL,
        {'action_type': ActionType.WRITE.value, 'environment': Environment.PRODUCTION.value},
    )

    response = client.post(
        f'/api/v1/agents/{agent.id}/authorize',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'action_type': 'WRITE',
            'resource_type': 'DATABASE',
            'operation': 'UPDATE_CUSTOMER',
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
    approval_id = response.json()['approval_request_id']
    assert approval_id is not None

    with SessionLocal() as session:
        event_types = {item.event_type for item in session.query(AuditEvent).filter_by(organization_id=organization.id).all()}
        assert AuditEventType.AGENT_CREATED in event_types or AuditEventType.RISK_EVALUATED in event_types
        assert AuditEventType.AUTHORIZATION_EVALUATED in event_types
        assert AuditEventType.APPROVAL_REQUESTED in event_types

    response = client.post(
        f'/api/v1/approvals/{approval_id}/approve',
        headers={'Authorization': f'Bearer {reviewer_token}'},
        json={'resolution_reason': 'Approved by owner.'},
    )
    assert response.status_code == 200, response.text

    with SessionLocal() as session:
        event_types = {item.event_type for item in session.query(AuditEvent).filter_by(organization_id=organization.id).all()}
        assert AuditEventType.APPROVAL_APPROVED in event_types


def test_audit_filters_and_pagination_are_stable():
    organization = _create_organization('FilterOrg')
    agent = _create_agent(organization, 'filter-agent')

    for i in range(4):
        _create_audit_event(
            organization,
            event_type=(AuditEventType.AUTH_LOGIN_SUCCESS if i % 2 == 0 else AuditEventType.AUTH_LOGOUT),
            summary=f'event-{i}',
            agent_id=str(agent.id),
            details={'sequence': i},
        )

    user = _create_user(organization, 'filter-user@audit.example', UserRole.ADMIN)
    token = _login(user, organization)

    response = client.get('/api/v1/audit/events?event_type=AUTH_LOGIN_SUCCESS&limit=2', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload['total'] >= 2
    assert all(item['event_type'] == 'AUTH_LOGIN_SUCCESS' for item in payload['items'])
    assert payload['limit'] == 2
    assert len(payload['items']) <= 2

    response = client.get('/api/v1/audit/events?created_after=2000-01-01T00:00:00Z&created_before=2100-01-01T00:00:00Z', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200

    response = client.get('/api/v1/audit/events?created_after=2100-01-01T00:00:00Z&created_before=2000-01-01T00:00:00Z', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 422
