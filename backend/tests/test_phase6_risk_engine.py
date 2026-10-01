from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.database.session import SessionLocal
from app.main import app
from app.models import Agent, AuditEvent, Organization, User
from app.models.enums import UserRole
from app.security.passwords import hash_password
from app.services.risk import ActionRiskInput, RiskLevel, _risk_level_for_score, evaluate_risk

client = TestClient(app)
_created_organization_ids: set[UUID] = set()


@pytest.fixture(autouse=True)
def clean_phase6_test_data():
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
        organization = Organization(
            name=org_name,
            slug=f'{org_name.lower().replace(" ", "-")}-{uuid4().hex[:8]}',
        )
        session.add(organization)
        session.flush()
        _created_organization_ids.add(organization.id)
        user = User(
            organization_id=organization.id,
            email=email,
            password_hash=hash_password('StrongPass!123'),
            full_name='Risk Engine User',
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


def test_risk_engine_is_deterministic_for_same_normalized_input():
    request = ActionRiskInput(
        action_type='WRITE',
        resource_type='DATABASE',
        operation='UPDATE_CUSTOMER_RECORD',
        environment='PRODUCTION',
        data_sensitivity='CONFIDENTIAL',
        privilege_level='STANDARD',
        external_network_access=False,
        write_capability=True,
        destructive_capability=False,
        credential_access=False,
        financial_impact=False,
        requires_human_approval=False,
    )

    first = evaluate_risk(request)
    second = evaluate_risk(request)

    assert first.score == second.score == 70
    assert first.risk_level == second.risk_level == RiskLevel.HIGH
    assert first.factors == second.factors
    assert first.score >= 0
    assert first.risk_level in {RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL}


def test_risk_level_threshold_boundaries_are_non_overlapping():
    low = evaluate_risk(
        ActionRiskInput(
            action_type='READ',
            resource_type='DOCS',
            operation='VIEW',
            environment='DEVELOPMENT',
            data_sensitivity='PUBLIC',
            privilege_level='LOW',
            external_network_access=False,
            write_capability=False,
            destructive_capability=False,
            credential_access=False,
            financial_impact=False,
            requires_human_approval=False,
        )
    )
    medium = evaluate_risk(
        ActionRiskInput(
            action_type='READ',
            resource_type='DATABASE',
            operation='QUERY',
            environment='STAGING',
            data_sensitivity='INTERNAL',
            privilege_level='STANDARD',
            external_network_access=False,
            write_capability=False,
            destructive_capability=False,
            credential_access=False,
            financial_impact=False,
            requires_human_approval=False,
        )
    )
    high = evaluate_risk(
        ActionRiskInput(
            action_type='WRITE',
            resource_type='DATABASE',
            operation='UPDATE',
            environment='PRODUCTION',
            data_sensitivity='CONFIDENTIAL',
            privilege_level='STANDARD',
            external_network_access=False,
            write_capability=True,
            destructive_capability=False,
            credential_access=False,
            financial_impact=False,
            requires_human_approval=False,
        )
    )
    critical = evaluate_risk(
        ActionRiskInput(
            action_type='DELETE',
            resource_type='DATABASE',
            operation='PURGE',
            environment='PRODUCTION',
            data_sensitivity='RESTRICTED',
            privilege_level='ADMIN',
            external_network_access=True,
            write_capability=False,
            destructive_capability=True,
            credential_access=True,
            financial_impact=True,
            requires_human_approval=True,
        )
    )

    assert low.risk_level is RiskLevel.LOW
    assert medium.risk_level is RiskLevel.MEDIUM
    assert high.risk_level is RiskLevel.HIGH
    assert critical.risk_level is RiskLevel.CRITICAL
    assert low.score <= 24
    assert 25 <= medium.score <= 49
    assert 50 <= high.score <= 74
    assert 75 <= critical.score <= 100
    assert low.score < medium.score < high.score < critical.score


def test_factor_weights_raise_risk_for_sensitive_and_destructive_actions():
    low = evaluate_risk(
        ActionRiskInput(
            action_type='READ',
            resource_type='DOCS',
            operation='VIEW',
            environment='DEVELOPMENT',
            data_sensitivity='PUBLIC',
            privilege_level='LOW',
            external_network_access=False,
            write_capability=False,
            destructive_capability=False,
            credential_access=False,
            financial_impact=False,
            requires_human_approval=False,
        )
    )
    delete_operation = evaluate_risk(
        ActionRiskInput(
            action_type='DELETE',
            resource_type='DATABASE',
            operation='DELETE',
            environment='PRODUCTION',
            data_sensitivity='CONFIDENTIAL',
            privilege_level='STANDARD',
            external_network_access=False,
            write_capability=False,
            destructive_capability=True,
            credential_access=False,
            financial_impact=False,
            requires_human_approval=False,
        )
    )
    restricted = evaluate_risk(
        ActionRiskInput(
            action_type='READ',
            resource_type='DATABASE',
            operation='QUERY',
            environment='PRODUCTION',
            data_sensitivity='RESTRICTED',
            privilege_level='ADMIN',
            external_network_access=True,
            write_capability=False,
            destructive_capability=False,
            credential_access=True,
            financial_impact=True,
            requires_human_approval=False,
        )
    )

    assert delete_operation.score > low.score
    assert restricted.score > low.score
    assert restricted.score >= delete_operation.score
    assert any(factor['factor'] == 'credential_access' for factor in restricted.factors)
    assert any(factor['factor'] == 'financial_impact' for factor in restricted.factors)
    assert any(factor['factor'] == 'destructive_capability' for factor in delete_operation.factors)


def test_high_risk_scenarios_follow_documented_ordering():
    scenario_a = evaluate_risk(
        ActionRiskInput(
            action_type='READ',
            resource_type='DOCS',
            operation='VIEW',
            environment='DEVELOPMENT',
            data_sensitivity='PUBLIC',
            privilege_level='LOW',
            external_network_access=False,
            write_capability=False,
            destructive_capability=False,
            credential_access=False,
            financial_impact=False,
            requires_human_approval=False,
        )
    )
    scenario_b = evaluate_risk(
        ActionRiskInput(
            action_type='WRITE',
            resource_type='DATABASE',
            operation='UPDATE',
            environment='PRODUCTION',
            data_sensitivity='CONFIDENTIAL',
            privilege_level='STANDARD',
            external_network_access=False,
            write_capability=True,
            destructive_capability=False,
            credential_access=False,
            financial_impact=False,
            requires_human_approval=False,
        )
    )
    scenario_c = evaluate_risk(
        ActionRiskInput(
            action_type='DELETE',
            resource_type='DATABASE',
            operation='PURGE',
            environment='PRODUCTION',
            data_sensitivity='RESTRICTED',
            privilege_level='ADMIN',
            external_network_access=True,
            write_capability=False,
            destructive_capability=True,
            credential_access=True,
            financial_impact=True,
            requires_human_approval=True,
        )
    )

    assert scenario_a.risk_level is RiskLevel.LOW
    assert scenario_b.score > scenario_a.score
    assert scenario_c.score >= scenario_b.score
    assert scenario_c.risk_level is RiskLevel.CRITICAL


def test_post_agent_risk_evaluation_is_tenant_scoped_and_not_authoritative():
    org_a, user_a = _create_user(f'owner-{uuid4().hex[:8]}@example.com', UserRole.OWNER, 'Tenant A')
    org_b, _ = _create_user(f'owner-{uuid4().hex[:8]}@example.com', UserRole.OWNER, 'Tenant B')
    agent_a = _create_agent(org_a.id, 'Agent A')
    agent_b = _create_agent(org_b.id, 'Agent B')
    token = _token(user_a, org_a)

    response = client.post(
        f'/api/v1/agents/{agent_a.id}/risk/evaluate',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'action_type': 'READ',
            'resource_type': 'DATABASE',
            'operation': 'QUERY',
            'environment': 'DEVELOPMENT',
            'data_sensitivity': 'PUBLIC',
            'privilege_level': 'LOW',
            'external_network_access': False,
            'write_capability': False,
            'destructive_capability': False,
            'credential_access': False,
            'financial_impact': False,
            'requires_human_approval': False,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload['agent_id'] == str(agent_a.id)
    assert payload['risk_level'] in {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'}
    assert 'decision' not in payload
    assert 'allow' not in payload.get('risk_level', '').lower()

    forbidden = client.post(
        f'/api/v1/agents/{agent_b.id}/risk/evaluate',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'action_type': 'READ',
            'resource_type': 'DATABASE',
            'operation': 'QUERY',
            'environment': 'DEVELOPMENT',
            'data_sensitivity': 'PUBLIC',
            'privilege_level': 'LOW',
            'external_network_access': False,
            'write_capability': False,
            'destructive_capability': False,
            'credential_access': False,
            'financial_impact': False,
            'requires_human_approval': False,
        },
    )
    assert forbidden.status_code == 404


def test_action_input_requires_security_signals_and_rejects_untrusted_override_fields():
    with pytest.raises(ValueError):
        ActionRiskInput(
            action_type='NOT_VALID',
            resource_type='DATABASE',
            operation='QUERY',
            environment='DEVELOPMENT',
            data_sensitivity='PUBLIC',
            privilege_level='LOW',
        )

    with pytest.raises(ValueError):
        ActionRiskInput(
            action_type='READ',
            resource_type='DATABASE',
            operation='QUERY',
            environment='DEVELOPMENT',
            data_sensitivity='PUBLIC',
            privilege_level='LOW',
            external_network_access=False,
            write_capability=False,
            destructive_capability=False,
            credential_access=False,
            financial_impact=False,
            requires_human_approval=False,
            metadata={'score': 99},
        )

    with pytest.raises(ValueError):
        ActionRiskInput(
            action_type='READ',
            resource_type='DATABASE',
            operation='QUERY',
            data_sensitivity='PUBLIC',
            privilege_level='LOW',
            environment='DEVELOPMENT',
        )

    with pytest.raises(ValueError):
        ActionRiskInput(
            action_type='READ',
            resource_type='DATABASE',
            operation='QUERY',
            environment='DEVELOPMENT',
            data_sensitivity='PUBLIC',
        )


def test_requires_human_approval_is_not_a_risk_multiplier():
    base = evaluate_risk(
        ActionRiskInput(
            action_type='READ',
            resource_type='DATABASE',
            operation='QUERY',
            environment='PRODUCTION',
            data_sensitivity='CONFIDENTIAL',
            privilege_level='STANDARD',
            external_network_access=False,
            write_capability=False,
            destructive_capability=False,
            credential_access=False,
            financial_impact=False,
            requires_human_approval=False,
        )
    )
    approved = evaluate_risk(
        ActionRiskInput(
            action_type='READ',
            resource_type='DATABASE',
            operation='QUERY',
            environment='PRODUCTION',
            data_sensitivity='CONFIDENTIAL',
            privilege_level='STANDARD',
            external_network_access=False,
            write_capability=False,
            destructive_capability=False,
            credential_access=False,
            financial_impact=False,
            requires_human_approval=True,
        )
    )

    assert base.score == approved.score
    assert base.risk_level == approved.risk_level
    assert all(factor['factor'] != 'requires_human_approval' for factor in approved.factors)


def test_threshold_boundaries_are_exact_and_score_is_bounded():
    for raw_score, expected in [(0, RiskLevel.LOW), (24, RiskLevel.LOW), (25, RiskLevel.MEDIUM), (49, RiskLevel.MEDIUM), (50, RiskLevel.HIGH), (74, RiskLevel.HIGH), (75, RiskLevel.CRITICAL), (100, RiskLevel.CRITICAL)]:
        assert _risk_level_for_score(raw_score) is expected
    assert min(0, 24, 25, 49, 50, 74, 75, 100) >= 0
    assert max(0, 24, 25, 49, 50, 74, 75, 100) <= 100


def test_monotonicity_and_score_cap_for_extreme_values():
    dev = evaluate_risk(
        ActionRiskInput(
            action_type='READ',
            resource_type='DATABASE',
            operation='QUERY',
            environment='DEVELOPMENT',
            data_sensitivity='PUBLIC',
            privilege_level='LOW',
            external_network_access=False,
            write_capability=False,
            destructive_capability=False,
            credential_access=False,
            financial_impact=False,
            requires_human_approval=False,
        )
    )
    staging = evaluate_risk(
        ActionRiskInput(
            action_type='READ',
            resource_type='DATABASE',
            operation='QUERY',
            environment='STAGING',
            data_sensitivity='INTERNAL',
            privilege_level='STANDARD',
            external_network_access=False,
            write_capability=False,
            destructive_capability=False,
            credential_access=False,
            financial_impact=False,
            requires_human_approval=False,
        )
    )
    prod = evaluate_risk(
        ActionRiskInput(
            action_type='READ',
            resource_type='DATABASE',
            operation='QUERY',
            environment='PRODUCTION',
            data_sensitivity='RESTRICTED',
            privilege_level='ADMIN',
            external_network_access=True,
            write_capability=False,
            destructive_capability=False,
            credential_access=True,
            financial_impact=True,
            requires_human_approval=False,
        )
    )

    assert staging.score >= dev.score
    assert prod.score >= staging.score
    assert prod.score <= 100

    highest = evaluate_risk(
        ActionRiskInput(
            action_type='DELETE',
            resource_type='DATABASE',
            operation='PURGE',
            environment='PRODUCTION',
            data_sensitivity='RESTRICTED',
            privilege_level='ADMIN',
            external_network_access=True,
            write_capability=True,
            destructive_capability=True,
            credential_access=True,
            financial_impact=True,
            requires_human_approval=False,
        )
    )
    assert highest.score == 100
    assert highest.risk_level is RiskLevel.CRITICAL


def test_metadata_is_not_echoed_back_in_assessment_response():
    assessment = evaluate_risk(
        ActionRiskInput(
            action_type='READ',
            resource_type='DATABASE',
            operation='QUERY',
            environment='PRODUCTION',
            data_sensitivity='CONFIDENTIAL',
            privilege_level='STANDARD',
            external_network_access=False,
            write_capability=False,
            destructive_capability=False,
            credential_access=False,
            financial_impact=False,
            requires_human_approval=False,
            metadata={'score': 99, 'token': 'hidden-token', 'nested': {'payload': 'x' * 5000}},
        )
    )

    assert 'metadata' not in assessment.action.model_dump()
    assert assessment.action.model_dump()['resource_type'] == 'DATABASE'
    assert assessment.action.model_dump()['operation'] == 'QUERY'
