# Aegent

Security and governance for autonomous AI agents.

## Frontend foundation

The Phase 10 frontend is a React + TypeScript + Vite application in `frontend/`.

```powershell
cd frontend
npm install
npm run dev
```

The development server proxies `/api` to `http://127.0.0.1:8000`. Start the FastAPI backend separately from `backend/`. Copy `frontend/.env.example` to `frontend/.env` only when the API is hosted at a different base URL; `VITE_API_BASE_URL` is client-visible and must not contain secrets.

Frontend checks:

```powershell
npm run lint
npm test
npm run build
```
# Aegent

Security and Governance for Autonomous AI Agents

Aegent is a security gateway for autonomous AI agents. It provides a foundation for policy enforcement, approval flows, and governance controls around agent actions.

## Current development status

### Implemented
- Repository cleanup and backend foundation setup
- FastAPI application skeleton with root and health endpoints
- Basic configuration environment template
- Modular backend package structure
- PostgreSQL configuration foundation
- SQLAlchemy and Alembic database foundation
- PostgreSQL domain models
- Authentication and authorization
- Tenant-scoped AI agent identity and management API

### Planned
- Policy evaluation and risk engine
- Audit logging and security event processing
- Frontend application
- Deployment and operational tooling

## Database technology
- PostgreSQL
- SQLAlchemy 2.x
- Alembic migrations

## Backend setup

From the repository root:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:DATABASE_URL = "postgresql+psycopg://username:password@localhost:5432/aegent"
uvicorn app.main:app --reload
```

Add the actual value for `DATABASE_URL` in a local `.env` file if you want to use environment-based configuration.

## Application URLs

- API root: http://127.0.0.1:8000/
- Health check: http://127.0.0.1:8000/health
- Database health check: http://127.0.0.1:8000/health/database
- API docs: http://127.0.0.1:8000/docs

## Notes

The project is currently in Phase 5: PostgreSQL + SQLAlchemy + Alembic foundation, authentication, authorization, and tenant-scoped agent identity management. The frontend remains out of scope for this phase.

## Agent API

Authenticated users can list and view agents only within their organization:

- `POST /api/v1/agents`
- `GET /api/v1/agents`
- `GET /api/v1/agents/{agent_id}`
- `PATCH /api/v1/agents/{agent_id}`
- `POST /api/v1/agents/{agent_id}/disable`

Agent creation, updates, and disabling require an `OWNER`, `ADMIN`, or `SECURITY_ANALYST` role. Organization ownership is always derived from the authenticated user context. `risk_level` is persisted metadata with a `LOW` default; risk calculation is not part of Phase 5.
