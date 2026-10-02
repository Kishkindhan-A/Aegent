from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.database.session import SessionLocal
from app.main import app
from app.models import Organization, User
from app.models.enums import UserRole, UserStatus
from app.security.passwords import hash_password

client = TestClient(app)


def _create_org(org_name: str):
    with SessionLocal() as session:
        org = Organization(name=org_name, slug=f"{org_name.lower().replace(' ', '-')}-{uuid4().hex[:8]}")
        session.add(org)
        session.commit()
        return {'slug': org.slug, 'id': org.id}


def _create_user(org_id, email: str, *, role: UserRole, status: UserStatus = UserStatus.ACTIVE):
    with SessionLocal() as session:
        user = User(
            organization_id=org_id,
            email=email,
            password_hash=hash_password('StrongPass!123'),
            full_name='Test User',
            role=role,
            status=status,
        )
        session.add(user)
        session.commit()
        return {'id': user.id, 'email': user.email}


def _login(email: str, org_slug: str):
    response = client.post(
        '/api/v1/auth/login',
        json={'email': email, 'password': 'StrongPass!123', 'organization_slug': org_slug},
    )
    assert response.status_code == 200, response.text
    return response.json()['access_token']


def test_organization_me_and_member_directory_are_tenant_scoped_and_role_restricted():
    org_a = _create_org('Org A')
    owner = _create_user(org_a['id'], 'owner-a@example.com', role=UserRole.OWNER)
    member = _create_user(org_a['id'], 'member-a@example.com', role=UserRole.MEMBER)
    other_org = _create_org('Org B')
    other_member = _create_user(other_org['id'], 'member-b@example.com', role=UserRole.MEMBER)

    owner_token = _login(owner['email'], org_a['slug'])
    member_token = _login(member['email'], org_a['slug'])
    other_member_token = _login(other_member['email'], other_org['slug'])

    profile = client.get('/api/v1/organizations/me', headers={'Authorization': f'Bearer {owner_token}'})
    assert profile.status_code == 200, profile.text
    assert profile.json()['slug'] == org_a['slug']

    directory = client.get('/api/v1/organizations/users', headers={'Authorization': f'Bearer {owner_token}'})
    assert directory.status_code == 200, directory.text
    assert directory.json()['total'] >= 2

    forbidden = client.get('/api/v1/organizations/users', headers={'Authorization': f'Bearer {member_token}'})
    assert forbidden.status_code == 403

    cross_tenant = client.get(f"/api/v1/organizations/users/{other_member['id']}", headers={'Authorization': f'Bearer {owner_token}'})
    assert cross_tenant.status_code == 404

    other_org_forbidden = client.get('/api/v1/organizations/users', headers={'Authorization': f'Bearer {other_member_token}'})
    assert other_org_forbidden.status_code == 403


def test_owner_can_update_organization_name_and_admins_can_manage_members_without_owner_transfer():
    org = _create_org('Org C')
    owner = _create_user(org['id'], 'owner-b@example.com', role=UserRole.OWNER)
    admin = _create_user(org['id'], 'admin-b@example.com', role=UserRole.ADMIN)
    member = _create_user(org['id'], 'member-c@example.com', role=UserRole.MEMBER)

    owner_token = _login(owner['email'], org['slug'])
    admin_token = _login(admin['email'], org['slug'])
    member_token = _login(member['email'], org['slug'])

    updated = client.patch(
        '/api/v1/organizations/me',
        json={'name': 'Org C Updated'},
        headers={'Authorization': f'Bearer {owner_token}'},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()['name'] == 'Org C Updated'

    slug_patch = client.patch(
        '/api/v1/organizations/me',
        json={'slug': 'new-slug'},
        headers={'Authorization': f'Bearer {owner_token}'},
    )
    assert slug_patch.status_code == 422

    role_change = client.patch(
        f"/api/v1/organizations/users/{member['id']}/role",
        json={'role': 'SECURITY_ANALYST'},
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert role_change.status_code == 200, role_change.text
    assert role_change.json()['role'] == 'SECURITY_ANALYST'

    owner_role = client.patch(
        f"/api/v1/organizations/users/{owner['id']}/role",
        json={'role': 'ADMIN'},
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert owner_role.status_code == 403

    self_escalation = client.patch(
        f"/api/v1/organizations/users/{admin['id']}/role",
        json={'role': 'OWNER'},
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert self_escalation.status_code == 403

    forbidden_member = client.patch(
        f"/api/v1/organizations/users/{member['id']}/role",
        json={'role': 'ADMIN'},
        headers={'Authorization': f'Bearer {member_token}'},
    )
    assert forbidden_member.status_code == 403


def test_member_status_changes_are_restricted_and_audit_events_are_recorded():
    org = _create_org('Org D')
    owner = _create_user(org['id'], 'owner-c@example.com', role=UserRole.OWNER)
    admin = _create_user(org['id'], 'admin-c@example.com', role=UserRole.ADMIN)
    member = _create_user(org['id'], 'member-d@example.com', role=UserRole.MEMBER)

    owner_token = _login(owner['email'], org['slug'])
    admin_token = _login(admin['email'], org['slug'])

    status_change = client.patch(
        f"/api/v1/organizations/users/{member['id']}/status",
        json={'status': 'SUSPENDED'},
        headers={'Authorization': f'Bearer {owner_token}'},
    )
    assert status_change.status_code == 200, status_change.text
    assert status_change.json()['status'] == 'SUSPENDED'

    self_suspend = client.patch(
        f"/api/v1/organizations/users/{admin['id']}/status",
        json={'status': 'DISABLED'},
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert self_suspend.status_code == 403

    audit_events = client.get('/api/v1/audit/events', headers={'Authorization': f'Bearer {owner_token}'}, params={'limit': 20})
    assert audit_events.status_code == 200, audit_events.text
    payload = audit_events.json()
    assert any(item['event_type'] in {'USER_ROLE_CHANGED', 'USER_STATUS_CHANGED', 'ORGANIZATION_UPDATED'} for item in payload['items'])


def test_role_and_status_updates_reject_unexpected_mass_assignment_fields():
    org = _create_org('Org E')
    owner = _create_user(org['id'], 'owner-e@example.com', role=UserRole.OWNER)
    member = _create_user(org['id'], 'member-e@example.com', role=UserRole.MEMBER)
    owner_token = _login(owner['email'], org['slug'])

    bad_role = client.patch(
        f"/api/v1/organizations/users/{member['id']}/role",
        json={'role': 'ADMIN', 'organization_id': '00000000-0000-0000-0000-000000000999', 'email': 'hijack@example.com'},
        headers={'Authorization': f'Bearer {owner_token}'},
    )
    assert bad_role.status_code == 422

    bad_status = client.patch(
        f"/api/v1/organizations/users/{member['id']}/status",
        json={'status': 'SUSPENDED', 'organization_id': '00000000-0000-0000-0000-000000000999', 'password_hash': 'hijack'},
        headers={'Authorization': f'Bearer {owner_token}'},
    )
    assert bad_status.status_code == 422
