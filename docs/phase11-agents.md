# Phase 11: Agent Workspace

The authenticated frontend exposes the tenant-scoped agent workspace at `/agents` and `/agents/:agentId`.

- Owners, admins, and security analysts can create, edit, and disable agents. Members can inspect agents but do not see mutation controls; the backend remains the authorization authority.
- Inventory filters use the backend's `status`, `agent_type`, and `risk_level` query parameters with bounded `offset`/`limit` pagination.
- The detail view separates persistent agent posture from one-off deterministic action risk assessments. Risk evaluation returns a score and backend factor explanations; it is not an authorization decision.
- Security scans submit transient content to the Phase 9 endpoint with a 20,000-character client limit. Findings render metadata, severity, rule IDs, reasons, and normalized offsets only. Scan content is not stored in browser storage or URLs.
- Disable is a reversible-state workflow from the UI: the agent becomes `DISABLED` and remains an auditable record. There is no hard-delete control.