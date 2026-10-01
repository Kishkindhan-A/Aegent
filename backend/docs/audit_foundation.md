# Audit event foundation

Aegent records security-sensitive lifecycle events as append-only audit records. Each event is created by trusted server-side logic, not by client input, and it is scoped to a single organization.

The audit trail follows the same lifecycle as the application:

Agent / Action -> Risk -> Policy -> Approval -> Audit event

Key principles:

- Audit events are immutable. They are append-only and never mutated through public API writes.
- Audit records are tenant-scoped and read only by OWNER, ADMIN, and SECURITY_ANALYST roles.
- Event details are explicitly allowlisted and sanitized to remove sensitive values such as passwords, access tokens, cookies, and secrets.
- Audit data is historical evidence only; it never changes authorization decisions.
- Future security detectors can emit events through the same taxonomy without changing the audit database contract.
