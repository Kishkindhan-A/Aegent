from __future__ import annotations

import re

from app.schemas.security import SecurityFinding
from app.security.detectors.normalization import normalize_security_text

JWT_RE = re.compile(r'(?i)\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)?\b')
PRIVATE_KEY_RE = re.compile(r'(?is)-----BEGIN\s+(?:RSA\s+|EC\s+|DSA\s+|OPENSSH\s+|PGP\s+)?PRIVATE\s+KEY-----')
EMAIL_RE = re.compile(r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b')
PHONE_RE = re.compile(r'(?i)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b')
CONNECTION_RE = re.compile(r'(?is)\b(?:postgres(?:ql)?|mysql|mongodb|redis|amqp|mssql|sqlserver)://[^\s"\'<>]+')
PASSWORD_RE = re.compile(r'(?is)\b(?:password|passphrase|passwd|pwd)\s*[:=]\s*["\']?[^\s"\'\n]{12,}["\']?')
API_KEY_RE = re.compile(r'(?is)\b(?:api[_ -]?key|client[_ -]?secret|access[_ -]?key|secret[_ -]?key|account[_ -]?key)\s*[:=]\s*["\']?([A-Za-z0-9_\-]{12,})["\']?')
TOKEN_RE = re.compile(r'(?is)\b(?:bearer\s+)?(?:access|refresh|session|auth|id)[_-]?token\s*[:=]\s*["\']?([A-Za-z0-9._~+/-]{16,})["\']?')


def _is_luhn_valid(number: str) -> bool:
    digits = [int(char) for char in number if char.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            doubled = digit * 2
            checksum += doubled if doubled < 10 else doubled - 9
        else:
            checksum += digit
    return checksum % 10 == 0


def _add_finding(findings: list[SecurityFinding], *, match: re.Match[str], category: str, rule_id: str, severity: str, reason: str) -> None:
    key = (category, rule_id, match.start(), match.end())
    if any(existing.category == category and existing.rule_id == rule_id and (existing.start_offset == match.start() and existing.end_offset == match.end()) for existing in findings):
        return
    findings.append(
        SecurityFinding(
            finding_type='SENSITIVE_DATA',
            category=category,
            rule_id=rule_id,
            severity=severity,
            reason=reason,
            start_offset=match.start(),
            end_offset=match.end(),
        )
    )


def _detect_payment_cards(text: str) -> list[SecurityFinding]:
    findings: list[SecurityFinding] = []
    for match in re.finditer(r'(?<!\d)(?:\d[ -]?){13,19}(?!\d)', text):
        candidate = match.group(0).replace(' ', '').replace('-', '')
        if len(candidate) < 13 or len(candidate) > 19:
            continue
        if not _is_luhn_valid(candidate):
            continue
        _add_finding(
            findings,
            match=match,
            category='PAYMENT_CARD',
            rule_id='SD-009',
            severity='HIGH',
            reason='Payment-card candidate passed deterministic Luhn validation.',
        )
    return findings


def detect_sensitive_data(content: str) -> list[SecurityFinding]:
    normalized = normalize_security_text(content)
    findings: list[SecurityFinding] = []

    for pattern, category, rule_id, severity, reason in [
        (JWT_RE, 'JWT', 'SD-001', 'HIGH', 'JWT-shaped credential detected.'),
        (PRIVATE_KEY_RE, 'PRIVATE_KEY', 'SD-002', 'CRITICAL', 'Private-key PEM structure detected.'),
        (PASSWORD_RE, 'PASSWORD_OR_CREDENTIAL', 'SD-003', 'HIGH', 'Password-like assignment with credential context detected.'),
        (API_KEY_RE, 'API_KEY', 'SD-004', 'HIGH', 'API-key assignment detected.'),
        (TOKEN_RE, 'ACCESS_TOKEN', 'SD-005', 'HIGH', 'Token-like credential detected.'),
        (CONNECTION_RE, 'CONNECTION_STRING', 'SD-006', 'HIGH', 'Database connection credential pattern detected.'),
        (EMAIL_RE, 'EMAIL_ADDRESS', 'SD-007', 'LOW', 'Email address pattern detected.'),
        (PHONE_RE, 'PHONE_NUMBER', 'SD-008', 'LOW', 'Phone number pattern detected.'),
    ]:
        for match in pattern.finditer(normalized):
            _add_finding(findings, match=match, category=category, rule_id=rule_id, severity=severity, reason=reason)

    findings.extend(_detect_payment_cards(normalized))
    findings.sort(key=lambda item: (item.start_offset or 0, item.rule_id, item.category))
    return findings
