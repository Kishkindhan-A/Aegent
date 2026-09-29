from __future__ import annotations

from typing import Any
from uuid import UUID

from app.models import Policy
from app.models.enums import ActionType, AgentRiskLevel, AgentType, ApprovalStatus, DataSensitivity, Environment, PolicyEffect, PrivilegeLevel
from app.schemas.policy import PolicyDecisionResult


_EFFECT_PRECEDENCE = {
    PolicyEffect.DENY: 3,
    PolicyEffect.REQUIRE_APPROVAL: 2,
    PolicyEffect.ALLOW: 1,
}


def _risk_level_order(level: str | AgentRiskLevel) -> int:
    values = {
        'LOW': 1,
        'MEDIUM': 2,
        'HIGH': 3,
        'CRITICAL': 4,
    }
    if isinstance(level, AgentRiskLevel):
        return values[level.value]
    return values.get(str(level).upper(), 0)


def _coerce_context(action_context: dict[str, Any] | Any) -> dict[str, Any]:
    if hasattr(action_context, 'model_dump'):
        return action_context.model_dump(exclude_none=True, mode='json')
    if isinstance(action_context, dict):
        return dict(action_context)
    return {}


def _coerce_risk(risk_assessment: dict[str, Any] | Any) -> dict[str, Any]:
    if hasattr(risk_assessment, 'model_dump'):
        return risk_assessment.model_dump(exclude_none=True, mode='json')
    if isinstance(risk_assessment, dict):
        return dict(risk_assessment)
    return {}


def _matches_condition(policy_condition: dict[str, Any], context: dict[str, Any], risk_assessment: dict[str, Any]) -> bool:
    for key, expected in (policy_condition or {}).items():
        if expected is None:
            continue
        if key == 'agent_id':
            actual = context.get('agent_id')
            if actual is None or str(actual) != str(expected):
                return False
            continue
        if key == 'agent_type':
            actual = context.get('agent_type')
            if actual is None or str(actual) != str(expected):
                return False
            continue
        if key == 'action_type':
            actual = context.get('action_type')
            if actual is None:
                return False
            if isinstance(actual, ActionType):
                actual = actual.value
            if str(actual) != str(expected):
                return False
            continue
        if key == 'environment':
            actual = context.get('environment')
            if actual is None:
                return False
            if isinstance(actual, Environment):
                actual = actual.value
            if str(actual) != str(expected):
                return False
            continue
        if key == 'data_sensitivity':
            actual = context.get('data_sensitivity')
            if actual is None:
                return False
            if isinstance(actual, DataSensitivity):
                actual = actual.value
            if str(actual) != str(expected):
                return False
            continue
        if key == 'privilege_level':
            actual = context.get('privilege_level')
            if actual is None:
                return False
            if isinstance(actual, PrivilegeLevel):
                actual = actual.value
            if str(actual) != str(expected):
                return False
            continue
        if key == 'minimum_risk_score':
            score = int(risk_assessment.get('score', 0) or 0)
            if score < int(expected):
                return False
            continue
        if key == 'minimum_risk_level':
            risk_level = str(risk_assessment.get('risk_level', 'LOW')).upper()
            if _risk_level_order(risk_level) < _risk_level_order(expected):
                return False
            continue
        if key in {'external_network_access', 'destructive_capability', 'credential_access', 'financial_impact'}:
            actual = bool(context.get(key, False))
            if actual != bool(expected):
                return False
            continue
        if key == 'agent_id':
            if str(context.get('agent_id')) != str(expected):
                return False
    return True


def evaluate_policy(action_context: dict[str, Any] | Any, risk_assessment: dict[str, Any] | Any, policies: list[Policy]) -> PolicyDecisionResult:
    normalized_context = _coerce_context(action_context)
    normalized_risk = _coerce_risk(risk_assessment)

    matches: list[Policy] = []
    for policy in policies:
        if not getattr(policy, 'enabled', True):
            continue
        if _matches_condition(policy.conditions or {}, normalized_context, normalized_risk):
            matches.append(policy)

    if not matches:
        return PolicyDecisionResult(
            decision=PolicyEffect.DENY,
            reason='No matching policy; default deny.',
            risk_score=int(normalized_risk.get('score', 0) or 0),
            risk_level=str(normalized_risk.get('risk_level', 'LOW')),
        )

    selected = sorted(
        matches,
        key=lambda policy: (
            int(getattr(policy, 'priority', 0) or 0),
            _EFFECT_PRECEDENCE.get(policy.effect, 0),
            str(policy.id),
        ),
        reverse=True,
    )[0]

    decision = selected.effect
    reason = f'Matched policy: {selected.name}.'
    return PolicyDecisionResult(
        decision=decision,
        matched_policy_id=selected.id,
        matched_policy_name=selected.name,
        matched_policy_effect=selected.effect,
        priority=int(selected.priority),
        reason=reason,
        risk_score=int(normalized_risk.get('score', 0) or 0),
        risk_level=str(normalized_risk.get('risk_level', 'LOW')),
        matched_details={'conditions': selected.conditions or {}},
    )
