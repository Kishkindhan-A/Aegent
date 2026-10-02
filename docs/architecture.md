# Aegent architecture

## Deployment topology

```text
Browser
  ↓ HTTPS
Reverse Proxy / Gateway
  ├── Frontend static app
  └── /api → FastAPI
                ↓
             PostgreSQL
```

## Real runtime components

### Frontend

- React + TypeScript + Vite
- static bundle served by reverse proxy or containerized Nginx
- API calls go through either same-origin routing or a deliberate `VITE_API_BASE_URL`

### Backend

- FastAPI service in `backend/app`
- routed modules:
  - Auth
  - Organizations
  - Agents
  - Risk
  - Policies
  - Approvals
  - Audit
  - Security detectors

### Data layer

- PostgreSQL primary database
- SQLAlchemy ORM + Alembic migrations
- DB connection pool with health checks and safe configuration defaults

## Security boundaries

- Auth uses tenant-scoped JWT validation and refresh rotation
- Role checks are enforced on the backend, not only in the UI
- Audit events are created server-side for sensitive mutations
- Sensitive values are redacted before being logged or returned in errors

## Operational notes

- Health endpoints are intentionally minimal and do not expose infrastructure secrets
- Deployment should enforce TLS termination, trusted hosts, and explicit CORS origins
- Application startup should fail clearly on unsafe production configuration
