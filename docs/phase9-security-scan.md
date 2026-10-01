# Phase 9 security scan foundation

The Phase 9 detector layer applies deterministic, explainable, bounded checks before any policy or approval decision is made.

## Flow

Content -> normalization -> prompt injection detection + sensitive-data detection -> structured security findings -> immutable audit event

## Deterministic design

- No external AI or LLM call is used.
- Rules are fixed, versioned, and stable.
- Results depend only on normalized content, not on randomness or model judgment.
- Input length is bounded to 20,000 characters.
- Raw content is inspected transiently in memory only and is never persisted or echoed back in full.

## Heuristic limits

This detector is intentional about being a heuristic security signal, not a perfect classifier. It uses stable regex- and pattern-based checks for prompt-injection and sensitive-data indicators, including known credential and secret formats.

It does not attempt to guarantee perfect PII coverage or complete confusable Unicode detection. Known limitations are documented as part of the implementation so that downstream enforcement remains explicit and separate from detection.

## Safety guarantees

- Detection does not authorize, deny, or approve actions.
- Security findings remain independent from the risk engine and policy engine.
- Sensitive matches are reported as categories, rule IDs, severity, and bounded offsets only.
- Full secrets, JWTs, private keys, passwords, API keys, or payment card numbers are never returned in API responses or audit details.

## Audit integration

When a scan reports prompt injection or sensitive data, the system emits immutable Phase 8 audit events of type PROMPT_INJECTION_DETECTED or SENSITIVE_DATA_DETECTED. These records contain only safe, structured summaries, never the original content or the exact secret value.

## Tenant protection

The scan endpoint is scoped to the authenticated user’s organization and verified agent ownership. Cross-tenant agent lookups return 404-style semantics and do not create events under another organization.
