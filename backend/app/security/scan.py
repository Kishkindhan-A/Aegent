from __future__ import annotations

from app.schemas.security import SecurityFinding, SecurityScanRequest, SecurityScanResult
from app.security.detectors.normalization import normalize_security_text
from app.security.detectors.prompt_injection import detect_prompt_injection
from app.security.detectors.sensitive_data import detect_sensitive_data

SEVERITY_ORDER = {
    'INFO': 0,
    'LOW': 1,
    'MEDIUM': 2,
    'HIGH': 3,
    'CRITICAL': 4,
}


def scan_security_content(request: SecurityScanRequest) -> SecurityScanResult:
    normalized = normalize_security_text(request.content)
    findings: list[SecurityFinding] = []
    findings.extend(detect_prompt_injection(normalized))
    findings.extend(detect_sensitive_data(normalized))
    findings = sorted(findings, key=lambda item: (item.start_offset or 0, item.rule_id, item.category))

    prompt_injection_detected = any(item.finding_type == 'PROMPT_INJECTION' for item in findings)
    sensitive_data_detected = any(item.finding_type == 'SENSITIVE_DATA' for item in findings)
    highest_finding_severity = None
    if findings:
        highest_finding_severity = max(
            (item.severity for item in findings),
            key=lambda value: SEVERITY_ORDER.get(value, -1),
        )

    return SecurityScanResult(
        prompt_injection_detected=prompt_injection_detected,
        sensitive_data_detected=sensitive_data_detected,
        finding_count=len(findings),
        highest_finding_severity=highest_finding_severity,
        findings=findings,
    )
