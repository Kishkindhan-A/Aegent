from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.database.session import SessionLocal
from app.main import app
from app.models import Organization, User, AuditEvent
from app.models.enums import UserRole, AuditEventType, ActorType, AuditEventCategory, EventSeverity
from app.security.passwords import hash_password

client = TestClient(app)
with SessionLocal() as s:
    s.execute(delete(AuditEvent))
    s.execute(delete(User))
    s.execute(delete(Organization))
    s.commit()

with SessionLocal() as s:
    org_a = Organization(name='OrgA', slug='orga-' + uuid4().hex[:8])
    org_b = Organization(name='OrgB', slug='orgb-' + uuid4().hex[:8])
    s.add_all([org_a, org_b])
    s.commit(); s.refresh(org_a); s.refresh(org_b)
    user_a = User(organization_id=org_a.id, email='usera@audit.example', password_hash=hash_password('StrongPass!123'), full_name='Audit User', role=UserRole.OWNER)
    user_b = User(organization_id=org_b.id, email='userb@audit.example', password_hash=hash_password('StrongPass!123'), full_name='Audit User', role=UserRole.ADMIN)
    s.add_all([user_a, user_b])
    s.commit(); s.refresh(user_a); s.refresh(user_b)
    s.add_all([
        AuditEvent(organization_id=org_a.id, event_type=AuditEventType.AUTH_LOGIN_SUCCESS, category=AuditEventCategory.AUTHENTICATION, severity=EventSeverity.INFO, actor_type=ActorType.USER, actor_user_id=user_a.id, correlation_id=str(uuid4()), source='test.audit', summary='OrgA login', details={}),
        AuditEvent(organization_id=org_b.id, event_type=AuditEventType.AUTH_LOGIN_SUCCESS, category=AuditEventCategory.AUTHENTICATION, severity=EventSeverity.INFO, actor_type=ActorType.USER, actor_user_id=user_b.id, correlation_id=str(uuid4()), source='test.audit', summary='OrgB login', details={}),
    ])
    s.commit()

resp = client.post('/api/v1/auth/login', json={'email':'usera@audit.example','password':'StrongPass!123','organization_id':str(org_a.id)})
print('login status', resp.status_code)
print(resp.text)
token = resp.json()['access_token']
resp2 = client.get('/api/v1/audit/events', headers={'Authorization': f'Bearer {token}'})
print('audit response status', resp2.status_code)
print(resp2.json())
