from __future__ import annotations

import enum

from pydantic import BaseModel, Field, field_validator

MAX_SECURITY_SCAN_CONTENT_LENGTH = 20000


class SecurityContentType(str, enum.Enum):
    PROMPT = 'PROMPT'
    TOOL_INPUT = 'TOOL_INPUT'
    TOOL_OUTPUT = 'TOOL_OUTPUT'
    RESPONSE = 'RESPONSE'
    TEXT = 'TEXT'


class SecuritySourceContext(str, enum.Enum):
    USER_INPUT = 'USER_INPUT'
    SYSTEM_CONTEXT = 'SYSTEM_CONTEXT'
    TOOL_OUTPUT = 'TOOL_OUTPUT'
    AGENT_RESPONSE = 'AGENT_RESPONSE'
    OTHER = 'OTHER'


class SecurityScanRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=MAX_SECURITY_SCAN_CONTENT_LENGTH)
    content_type: SecurityContentType = SecurityContentType.TEXT
    source_context: SecuritySourceContext | None = None

    @field_validator('content')
    @classmethod
    def validate_content_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError('content must not be blank.')
        return value


class SecurityFinding(BaseModel):
    """Structured finding metadata.

    Offsets refer to the normalized content inspected by the detector, not the
    original user payload. Normalization removes zero-width characters and
    collapses whitespace before matching.
    """

    finding_type: str
    category: str
    rule_id: str
    severity: str
    reason: str
    start_offset: int | None = None
    end_offset: int | None = None


class SecurityScanResult(BaseModel):
    prompt_injection_detected: bool
    sensitive_data_detected: bool
    finding_count: int
    highest_finding_severity: str | None = None
    findings: list[SecurityFinding]
    scan_version: str = 'phase9-v1'


class SecurityAuditSummary(BaseModel):
    agent_id: str | None = None
    finding_count: int = 0
    categories: list[str] = []
    rule_ids: list[str] = []
    highest_severity: str | None = None
    content_type: str | None = None
