from __future__ import annotations

import json

from sentra.fallbacks import build_rule_based_risk
from sentra.llm import LLMConfigError, LLMResponseError, llm_enabled, structured_completion
from sentra.schemas import RiskAssessmentSchema
from sentra.state import TradingState


def assess_risk(state: TradingState) -> tuple[dict, str, str | None]:
    baseline = build_rule_based_risk(state)
    risk_score = baseline["base_risk_score"]
    risk_level = baseline["risk_level"]
    risk_reasons = list(baseline["risk_reasons"])
    rule_flags = list(baseline["rule_flags"])
    fallback_error: str | None = None

    if llm_enabled():
        system_prompt = (
            "You are an independent risk officer. Assess trading risk as structured JSON. "
            "Consider volatility, setup quality, data quality, and position sizing. "
            "You may raise risk above the rule-based floor, but never ignore the provided rule flags."
        )
        user_prompt = (
            f"Query: {state.get('query', '')}\n"
            f"Strategy: {json.dumps(state.get('strategy', {}), default=str)}\n"
            f"Analysis: {json.dumps(state.get('analysis', {}), default=str)}\n"
            f"Market data: {json.dumps(state.get('market_data', {}), default=str)}\n"
            f"Technical data: {json.dumps(state.get('technical_data', {}), default=str)}\n"
            f"Rule flags: {json.dumps(rule_flags)}\n"
            f"Base risk score floor: {risk_score}\n"
            "Return a structured risk assessment."
        )
        try:
            parsed = structured_completion(
                RiskAssessmentSchema,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            risk_score = max(risk_score, parsed.risk_score)
            risk_reasons = risk_reasons + [
                reason for reason in parsed.risk_reasons if reason not in risk_reasons
            ]
            source = "llm"
        except (LLMConfigError, LLMResponseError, Exception) as exc:
            fallback_error = str(exc)
            source = "fallback"
    else:
        source = "fallback"

    requires_human_review = bool(
        rule_flags or risk_score > 0.7 or state.get("data_quality_flags")
    )
    if requires_human_review and risk_score < 0.7:
        risk_score = max(risk_score, 0.7)

    if risk_score >= 0.7:
        risk_level = "high"
    elif risk_score >= 0.4:
        risk_level = "medium"
    else:
        risk_level = "low"

    assessment = {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_reasons": risk_reasons,
        "rule_flags": rule_flags,
        "requires_human_review": requires_human_review,
    }
    return assessment, source, fallback_error


def risk_officer_node(state: TradingState) -> TradingState:
    assessment, _, _ = assess_risk(state)
    return assessment
