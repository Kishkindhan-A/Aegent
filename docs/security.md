# Security overview

## Authentication and authorization

Aegent uses tenant-aware authentication with backend-authoritative role checks. The system keeps the current user identity and role in the database and validates the effective authorization on each request. Refresh tokens rotate on use, and expired or revoked tokens are denied.

## Deterministic security controls

The project intentionally uses deterministic risk and policy evaluation instead of allowing an LLM to make final authorization decisions. Risk factors and policy matches remain explainable and auditable.

## Sensitive data handling

- Passwords are hashed before storage.
- API tokens and credential-like data are not logged in raw form.
- Security scan payloads and prompt content are not written to logs without redaction.
- Validation errors are sanitized so secret fields do not appear in responses.

## Logging and observability

The application emits request-level information with a generated request ID, method, path, status code, and timing data. Sensitive keys such as `password`, `token`, `secret`, `authorization`, `cookie`, `api_key`, and database connection values are redacted recursively before log output.

## Production HTTP controls

The hardened backend enforces:

- explicit CORS allowlists
- configured trusted hosts
- security headers appropriate to the application layer
- request-size limits
- bounded rate limiting for abuse-sensitive endpoints

These controls reduce specific risks but do not replace reverse-proxy or CDN enforcement when those layers are deployed in front of the app.

## Frontend token limitation

The current frontend refresh-token model keeps the refresh credential in `sessionStorage` because the backend refresh contract is body-based and the project has not migrated to a cookie-based architecture. This is treated as a known production limitation and not as a false claim of ideal security.

## Vulnerability reporting

If a potential security issue is discovered, it should be reported privately and fixed before broad disclosure. No product claim should state that all attacks are prevented or that the system is "100% secure" without evidence.
