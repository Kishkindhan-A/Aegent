# Deployment guide

## Production topology

Aegent is designed to run behind a TLS termination layer such as a reverse proxy or ingress controller. The frontend can be served as a static bundle, while the backend serves the JSON API under `/api`.

## Required environment configuration

Set the backend environment with explicit values for:

- `APP_ENV`
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `CORS_ALLOWED_ORIGINS`
- `TRUSTED_HOSTS`
- `LOG_LEVEL`
- `MAX_REQUEST_SIZE_BYTES`
- `RATE_LIMIT_REQUESTS_PER_MINUTE`

The frontend should either use a same-origin deployment model or a deliberate `VITE_API_BASE_URL`.

## Release flow

1. Provision PostgreSQL.
2. Set non-production-safe environment values for runtime use.
3. Run database migrations:
   `python -m alembic upgrade head`
4. Start the backend process with the production settings.
5. Serve the frontend bundle through the reverse proxy or a static web server.
6. Check `/`, `/health`, `/health/database`, and `/docs`.

## Health and readiness

The app exposes basic health endpoints:

- `/`
- `/health`
- `/health/database`

These are intentionally minimal and do not expose database credentials or internal stack traces.

## Backups and operations

Database backups should be handled outside the application process using PostgreSQL-native backup tooling or the team’s standard infrastructure process. The application should not contain custom backup logic that is fragile or tightly coupled to runtime state.

## Known limitations

- Rate limiting is currently process-local unless a shared backend store is introduced.
- Refresh-token storage remains in session storage under the current auth contract.
- Reverse-proxy-specific headers such as HSTS and CDN policy should be enforced at that deployment boundary.
