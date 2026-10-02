# Aegent

Security and governance for autonomous AI agents.

Aegent is the backend and frontend foundation for secure AI-agent governance, with tenant-aware authentication, policy and approval workflows, risk evaluation, audit logging, and admin controls.

## Project status

This repository is in a production-hardening and release-readiness pass derived from the project’s cross-cutting security and deployment requirements in [docs/Masterprompt.md](docs/Masterprompt.md). The work focuses on configuration safety, HTTP hardening, logging redaction, error hygiene, deployment documentation, CI checks, and regression validation.

## Architecture summary

- Frontend: React + TypeScript + Vite in `frontend/`
- Backend: FastAPI + SQLAlchemy + Alembic + PostgreSQL in `backend/`
- Auth: tenant-aware JWT flow with refresh rotation and DB-authoritative role checks
- Governance: policies, approvals, audit events, and security scans
- Deployment boundary: reverse proxy or same-origin routing in front of the FastAPI API

## Prerequisites

- Python 3.12+
- PostgreSQL
- Node.js 20+
- npm
- Git

## Backend setup

```powershell
cd backend
Copy-Item .env.example .env
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Important notes:

- Copy `.env.example` to `.env` and set a strong `JWT_SECRET_KEY` for local development.
- Do not commit real credentials or production values.
- Keep `APP_ENV=development` for local use; use `APP_ENV=production` only with strong, non-placeholder values.

## Frontend setup

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`. In production, leave `VITE_API_BASE_URL` empty to use the same-origin deployment model, or set it to a deliberate API origin.

## Database and migrations

```powershell
cd backend
python -m alembic current
python -m alembic heads
python -m alembic upgrade head
```

Production release steps should include applying the current Alembic head before starting the new application version.

## Tests

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m pytest tests -q

cd ..\frontend
npm run lint
npm test
npm run build
```

## Production configuration

Key environment variables are documented in the backend and frontend `.env.example` files. In production, the application rejects:

- empty or placeholder JWT secrets
- wildcard CORS origins with credentialed requests
- empty or invalid trusted-host lists
- unsafe request-size and rate-limit values

## Docker

Production-oriented Docker files are included for local/container validation when Docker is available:

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `.dockerignore`

These intentionally run the app without development reloads and without baking secrets into the image.

## CI

A minimal GitHub Actions workflow is included at `.github/workflows/ci.yml` for backend and frontend validation using real PostgreSQL for backend tests.

## Security considerations

- Refresh tokens remain in session storage by design for the current contract; this is documented as a known limitation rather than a false claim of ideal production security.
- Backend HTTP hardening includes safe CORS, host validation, security headers, request IDs, rate limiting, and redacted logging.
- Validation errors and unexpected exceptions are sanitized so they do not leak secrets or internal exception details.
- The project intentionally does not make exaggerated security claims beyond what is actually implemented and tested.

## Documentation

See:

- [docs/architecture.md](docs/architecture.md)
- [docs/security.md](docs/security.md)
- [docs/deployment.md](docs/deployment.md)

## Known limitations

- Refresh token persistence remains session-scoped for the current backend contract.
- In-process rate limiting is documented as process-local and is not a distributed production limiter.
- Reverse-proxy/CDN security policies still need to be enforced in the deployment layer when used outside the application itself.
