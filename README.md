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

### Planned
- PostgreSQL domain models
- Authentication and authorization
- AI agent identity and resource permissions
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

This project is currently in Phase 2: PostgreSQL + SQLAlchemy + Alembic foundation. Domain models and authentication layers are still planned, and the frontend remains out of scope for this phase.
