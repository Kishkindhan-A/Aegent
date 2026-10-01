from __future__ import annotations

import re
from typing import Final

from app.schemas.security import SecurityFinding
from app.security.detectors.normalization import normalize_security_text

PI_PATTERNS: Final[list[tuple[re.Pattern[str], str, str, str, str]]]
PI_PATTERNS = [
    (
        re.compile(r'(?is)(?:ignore|disregard|override|bypass|forget|skip)\s+(?:all\s+)?(?:previous|prior|earlier|hidden|system|developer|internal)\s+(?:instructions?|prompt|rules?|guardrails?|directives?)\s*(?:and|then|;|,|\.)?\s*(?:reveal|show|print|display|expose|override|bypass|share|leak|act\s+as|run|execute|trigger|send)'),
        'PROMPT_INJECTION',
        'INSTRUCTION_OVERRIDE',
        'PI-001',
        'HIGH',
    ),
    (
        re.compile(r'(?is)(?:reveal|show|print|display|expose|leak)\s+(?:the\s+)?(?:hidden|internal|developer|system|original)?(?:\s+(?:hidden|internal|developer|system|original))?\s*(?:instructions?|prompt|message|rules?)'),
        'PROMPT_INJECTION',
        'SYSTEM_PROMPT_EXTRACTION',
        'PI-002',
        'HIGH',
    ),
    (
        re.compile(r'(?is)(?:ignore|bypass|override|skip)\s+(?:all\s+)?(?:security\s+)?(?:policy|approval|guardrail|restriction|rule|validation)(?:\s+(?:and|or)\s+(?:security\s+)?(?:policy|approval|guardrail|restriction|rule|validation))?\s*(?:checks?|controls?|warnings?|enforcement|decisions?)?'),
        'PROMPT_INJECTION',
        'POLICY_BYPASS',
        'PI-003',
        'HIGH',
    ),
    (
        re.compile(r'(?is)(?:act\s+as|pretend\s+you\s+are|roleplay\s+as|you\s+are\s+now|assume\s+the\s+role\s+of)\s+(?:the\s+)?(?:[a-z]+\s+)?(?:admin|system|developer|owner|security|root)\b'),
        'PROMPT_INJECTION',
        'ROLE_MANIPULATION',
        'PI-004',
        'MEDIUM',
    ),
    (
        re.compile(r'(?is)(?:run|execute|call|invoke|trigger|send)\s+(?:the\s+)?(?:tool|script|command|shell|browser|network|api)\s+(?:without|ignoring)\s+(?:approval|permission|guardrail|policy|authorization)'),
        'PROMPT_INJECTION',
        'TOOL_MISUSE',
        'PI-005',
        'HIGH',
    ),
    (
        re.compile(r'(?is)(?:reveal|show|print|display|exfiltrate|share|leak)\s+(?:the\s+)?(?:secret|password|api\s*key|token|credential|jwt|private\s+key)\b'),
        'PROMPT_INJECTION',
        'SECRET_EXFILTRATION_REQUEST',
        'PI-006',
        'HIGH',
    ),
]


def _add_finding(findings: list[SecurityFinding], *, match: re.Match[str], category: str, rule_id: str, severity: str) -> None:
    key = (category, rule_id, match.start(), match.end())
    if any(existing.category == category and existing.rule_id == rule_id and (existing.start_offset == match.start() and existing.end_offset == match.end()) for existing in findings):
        return
    findings.append(
        SecurityFinding(
            finding_type='PROMPT_INJECTION',
            category=category,
            rule_id=rule_id,
            severity=severity,
            reason='Prompt-injection pattern matched a control-override instruction.',
            start_offset=match.start(),
            end_offset=match.end(),
        )
    )


def detect_prompt_injection(content: str) -> list[SecurityFinding]:
    normalized = normalize_security_text(content)
    findings: list[SecurityFinding] = []
    for pattern, finding_type, category, rule_id, severity in PI_PATTERNS:
        for match in pattern.finditer(normalized):
            _add_finding(findings, match=match, category=category, rule_id=rule_id, severity=severity)
    findings.sort(key=lambda item: (item.start_offset or 0, item.rule_id, item.category))
    return findings
