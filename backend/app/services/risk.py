from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.models.enums import ActionType, AgentRiskLevel, DataSensitivity, Environment, PrivilegeLevel
from app.schemas.risk import ActionRiskInput, RiskActionSummary, RiskAssessmentResponse

RiskLevel = AgentRiskLevel

ACTION_WEIGHT_BY_TYPE = {
    ActionType.READ: 5,
    ActionType.WRITE: 15,
    ActionType.DELETE: 30,
    ActionType.EXECUTE: 25,
    ActionType.NETWORK: 28,
    ActionType.TRANSFER: 35,
    ActionType.ADMIN: 40,
}

ENVIRONMENT_WEIGHT_BY_TYPE = {
    Environment.DEVELOPMENT: 0,
    Environment.STAGING: 10,
    Environment.PRODUCTION: 20,
}

SENSITIVITY_WEIGHT_BY_LEVEL = {
    DataSensitivity.PUBLIC: 0,
    DataSensitivity.INTERNAL: 10,
    DataSensitivity.CONFIDENTIAL: 20,
    DataSensitivity.RESTRICTED: 30,
}

PRIVILEGE_WEIGHT_BY_LEVEL = {
    PrivilegeLevel.LOW: 0,
    PrivilegeLevel.STANDARD: 10,
    PrivilegeLevel.ELEVATED: 20,
    PrivilegeLevel.ADMIN: 30,
}


def _risk_level_for_score(score: int) -> AgentRiskLevel:
    if score <= 24:
        return AgentRiskLevel.LOW
    if score <= 49:
        return AgentRiskLevel.MEDIUM
    if score <= 74:
        return AgentRiskLevel.HIGH
    return AgentRiskLevel.CRITICAL


def _append_factor(factors: list[dict[str, object]], *, factor: str, weight: int, reason: str) -> None:
    if weight <= 0:
        return
    factors.append({
        'factor': factor,
        'weight': weight,
        'reason': reason,
    })


def evaluate_risk(input_payload: ActionRiskInput, *, agent_id: UUID | None = None) -> RiskAssessmentResponse:
    """Evaluate a proposed AI-agent action using offline, deterministic security factors.

    The score is intentionally based only on explicit, non-LLM, non-network signals. Risk
    evaluation is informational and not authorization; it does not return allow/deny decisions.
    """

    score = 0
    factors: list[dict[str, object]] = []

    action_weight = ACTION_WEIGHT_BY_TYPE[input_payload.action_type]
    score += action_weight
    _append_factor(
        factors,
        factor='action_type',
        weight=action_weight,
        reason=f'{input_payload.action_type.value} actions have an explicit baseline risk contribution.',
    )

    environment_weight = ENVIRONMENT_WEIGHT_BY_TYPE[input_payload.environment]
    score += environment_weight
    _append_factor(
        factors,
        factor='environment',
        weight=environment_weight,
        reason='Production and staging workloads increase risk compared with development-only execution.',
    )

    sensitivity_weight = SENSITIVITY_WEIGHT_BY_LEVEL[input_payload.data_sensitivity]
    score += sensitivity_weight
    _append_factor(
        factors,
        factor='data_sensitivity',
        weight=sensitivity_weight,
        reason='Higher-sensitivity data requires stricter scrutiny because the impact of disclosure is greater.',
    )

    privilege_weight = PRIVILEGE_WEIGHT_BY_LEVEL[input_payload.privilege_level]
    score += privilege_weight
    _append_factor(
        factors,
        factor='privilege_level',
        weight=privilege_weight,
        reason='Higher-privilege operations increase blast radius and require tighter risk controls.',
    )

    if input_payload.external_network_access:
        network_weight = 15
        score += network_weight
        _append_factor(
            factors,
            factor='external_network_access',
            weight=network_weight,
            reason='External network access expands the action surface and increases exfiltration risk.',
        )

    if input_payload.write_capability:
        write_weight = 5
        score += write_weight
        _append_factor(
            factors,
            factor='write_capability',
            weight=write_weight,
            reason='Write capability can modify state, which increases downstream impact.',
        )

    if input_payload.destructive_capability:
        destructive_weight = 25
        score += destructive_weight
        _append_factor(
            factors,
            factor='destructive_capability',
            weight=destructive_weight,
            reason='Destructive operations can remove or corrupt business-critical data and state.',
        )

    if input_payload.credential_access:
        credential_weight = 20
        score += credential_weight
        _append_factor(
            factors,
            factor='credential_access',
            weight=credential_weight,
            reason='Credential or secret access raises the risk of unauthorized privilege escalation or lateral movement.',
        )

    if input_payload.financial_impact:
        financial_weight = 15
        score += financial_weight
        _append_factor(
            factors,
            factor='financial_impact',
            weight=financial_weight,
            reason='Financial impact indicators imply materially higher operational and compliance exposure.',
        )

    score = min(score, 100)
    risk_level = _risk_level_for_score(score)
    response = RiskAssessmentResponse(
        agent_id=agent_id,
        action=RiskActionSummary.model_validate({
            'action_type': input_payload.action_type,
            'resource_type': input_payload.resource_type,
            'operation': input_payload.operation,
            'environment': input_payload.environment,
            'data_sensitivity': input_payload.data_sensitivity,
            'privilege_level': input_payload.privilege_level,
            'external_network_access': input_payload.external_network_access,
            'write_capability': input_payload.write_capability,
            'destructive_capability': input_payload.destructive_capability,
            'credential_access': input_payload.credential_access,
            'financial_impact': input_payload.financial_impact,
            'requires_human_approval': input_payload.requires_human_approval,
        }),
        score=score,
        risk_level=risk_level,
        factors=factors,
        evaluated_at=datetime.now(timezone.utc),
    )
    return response
