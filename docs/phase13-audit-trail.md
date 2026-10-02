# Phase 13 — Audit trail and security investigation UI

The audit workspace is intentionally read-only. It exposes the tenant-scoped event history that the backend records as append-only audit facts, and it does not create, update, or resolve audit records.

## Read-only audit model

- The event inventory is tenant-scoped and filtered by backend authorization.
- OWNER, ADMIN, and SECURITY_ANALYST can view the audit trail.
- MEMBER access is blocked by the backend and the UI does not surface the audit navigation for that role.
- Events are ordered newest-first by the backend and the frontend respects that ordering.

## Security event handling

Security detector events such as PROMPT_INJECTION_DETECTED and SENSITIVE_DATA_DETECTED are treated as historical audit facts, not as active security decisions. The UI highlights those events without implying an active attack or unsafe status beyond the backend record itself.

The frontend never renders raw prompt content, raw secrets, JWTs, passwords, API keys, or other sensitive values. It only displays the sanitized details and metadata returned by the server.

## Investigation flow

The audit workspace supports:

- inventory filtering by backend-supported fields
- pagination bounded by backend limits
- event detail inspection
- correlation-based investigation through correlation_id
- chronological event timelines for related activities
- safe actor, agent, policy, and approval references

The purpose is to help an authorized security reviewer understand who performed an action, what happened, when it happened, and whether the event belongs to a related authorization lifecycle.

Audit history records what happened. It does not make authorization decisions.
