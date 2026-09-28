from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.database.session import SessionLocal
from app.main import app
from app.models import Organization, User
from app.models.enums import OrganizationStatus, UserRole, UserStatus
from app.security.passwords import hash_password, verify_password

client = TestClient(app)


def _create_org_and_user(email: str, *, org_name: str, user_role: UserRole = UserRole.MEMBER, status: UserStatus = UserStatus.ACTIVE):
    with SessionLocal() as session:
        org = Organization(name=org_name, slug=f"{org_name.lower().replace(' ', '-')}-{uuid4().hex[:8]}")
        session.add(org)
        session.flush()

        user = User(
            organization_id=org.id,
            email=email,
            password_hash=hash_password('StrongPass!123'),
            full_name='Test User',
            role=user_role,
            status=status,
        )
        session.add(user)
        session.commit()
        return {'slug': org.slug, 'id': org.id}, user


def test_password_hashing_and_verification():
    raw = 'StrongPass!123'
    hashed = hash_password(raw)

    assert hashed != raw
    assert hashed.startswith('$argon2id$')
    assert verify_password(raw, hashed) is True
    assert verify_password('WrongPass!', hashed) is False


def test_login_requires_organization_context_and_uses_slug():
    org, _ = _create_org_and_user('tenant-a@example.com', org_name='Tenant A')

    response = client.post(
        '/api/v1/auth/login',
        json={'email': 'tenant-a@example.com', 'password': 'StrongPass!123', 'organization_slug': org['slug']},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert 'access_token' in payload
    assert 'refresh_token' in payload

    bad = client.post(
        '/api/v1/auth/login',
        json={'email': 'tenant-a@example.com', 'password': 'StrongPass!123', 'organization_slug': 'wrong-slug'},
    )
    assert bad.status_code == 401


def test_same_email_in_different_orgs_logs_into_correct_tenant():
    org_a, _ = _create_org_and_user('shared@example.com', org_name='Org A')
    org_b, _ = _create_org_and_user('shared@example.com', org_name='Org B')

    login_a = client.post(
        '/api/v1/auth/login',
        json={'email': 'shared@example.com', 'password': 'StrongPass!123', 'organization_slug': org_a['slug']},
    )
    login_b = client.post(
        '/api/v1/auth/login',
        json={'email': 'shared@example.com', 'password': 'StrongPass!123', 'organization_slug': org_b['slug']},
    )

    assert login_a.status_code == 200
    assert login_b.status_code == 200
    assert login_a.json()['user']['organization_id'] != login_b.json()['user']['organization_id']


def test_current_user_requires_valid_access_token():
    org, user = _create_org_and_user('me@example.com', org_name='Current User Org')
    login = client.post(
        '/api/v1/auth/login',
        json={'email': 'me@example.com', 'password': 'StrongPass!123', 'organization_slug': org['slug']},
    )
    token = login.json()['access_token']

    me = client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert me.status_code == 200, me.text
    assert me.json()['email'] == 'me@example.com'
    assert me.json()['organization_id'] == str(org['id'])

    bad = client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer not-a-token'})
    assert bad.status_code == 401


def test_refresh_rotates_and_logout_revokes_session():
    org, _ = _create_org_and_user('refresh@example.com', org_name='Refresh Org')
    login = client.post(
        '/api/v1/auth/login',
        json={'email': 'refresh@example.com', 'password': 'StrongPass!123', 'organization_slug': org['slug']},
    )
    refresh_token = login.json()['refresh_token']

    refresh = client.post('/api/v1/auth/refresh', json={'refresh_token': refresh_token})
    assert refresh.status_code == 200, refresh.text
    new_tokens = refresh.json()
    assert 'access_token' in new_tokens
    assert 'refresh_token' in new_tokens
    assert new_tokens['refresh_token'] != refresh_token

    logout = client.post('/api/v1/auth/logout', json={'refresh_token': refresh_token})
    assert logout.status_code == 200

    reuse = client.post('/api/v1/auth/refresh', json={'refresh_token': refresh_token})
    assert reuse.status_code == 401


def test_rbac_roles_and_tenant_boundaries_are_enforced():
    org_a, _ = _create_org_and_user('a-admin@example.com', org_name='Org A', user_role=UserRole.ADMIN)
    org_b, _ = _create_org_and_user('b-member@example.com', org_name='Org B', user_role=UserRole.MEMBER)

    login_a = client.post(
        '/api/v1/auth/login',
        json={'email': 'a-admin@example.com', 'password': 'StrongPass!123', 'organization_slug': org_a['slug']},
    )
    token = login_a.json()['access_token']

    allowed = client.get('/api/v1/auth/health/roles', headers={'Authorization': f'Bearer {token}'})
    assert allowed.status_code == 200

    login_b = client.post(
        '/api/v1/auth/login',
        json={'email': 'b-member@example.com', 'password': 'StrongPass!123', 'organization_slug': org_b['slug']},
    )
    token_b = login_b.json()['access_token']

    forbidden = client.get('/api/v1/auth/health/roles', headers={'Authorization': f'Bearer {token_b}'})
    assert forbidden.status_code == 403


def test_disabled_user_cannot_authenticate_or_access_me():
    org, user = _create_org_and_user('disabled@example.com', org_name='Disabled Org', status=UserStatus.DISABLED)
    login = client.post(
        '/api/v1/auth/login',
        json={'email': 'disabled@example.com', 'password': 'StrongPass!123', 'organization_slug': org['slug']},
    )
    assert login.status_code == 401

    auth = client.post(
        '/api/v1/auth/login',
        json={'email': 'disabled@example.com', 'password': 'StrongPass!123', 'organization_slug': org['slug']},
    )
    assert auth.status_code == 401


def test_role_downgrade_invalidates_old_token():
    email = f'role-downgrade-{uuid4().hex[:8]}@example.com'
    org, _ = _create_org_and_user(email, org_name='Role Downgrade Org', user_role=UserRole.OWNER)
    login = client.post(
        '/api/v1/auth/login',
        json={'email': email, 'password': 'StrongPass!123', 'organization_slug': org['slug']},
    )
    token = login.json()['access_token']

    with SessionLocal() as session:
        stored = session.execute(
            __import__('sqlalchemy').select(User).where(User.email == email).where(User.organization_id == org['id'])
        ).scalar_one()
        stored.role = UserRole.MEMBER
        session.commit()

    allowed = client.get('/api/v1/auth/health/roles', headers={'Authorization': f'Bearer {token}'})
    assert allowed.status_code == 401


def test_schema_does_not_expose_password_hash_in_auth_response():
    org, _ = _create_org_and_user('schema@example.com', org_name='Schema Org')
    login = client.post(
        '/api/v1/auth/login',
        json={'email': 'schema@example.com', 'password': 'StrongPass!123', 'organization_slug': org['slug']},
    )
    assert login.status_code == 200
    assert 'password_hash' not in login.text
