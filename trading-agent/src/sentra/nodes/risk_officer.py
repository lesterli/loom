from sentra.state import TradingState


def risk_officer_node(state: TradingState) -> TradingState:
    strategy = state.get("strategy", {})
    analysis = state.get("analysis", {})
    rule_flags: list[str] = []
    risk_reasons: list[str] = []

    if strategy.get("position_size_pct", 0.0) > 25.0:
        rule_flags.append("oversized_position")
        risk_reasons.append("Proposed position size is too large for the demo risk policy.")

    if analysis.get("confidence", 0.0) < 0.55:
        rule_flags.append("low_confidence")
        risk_reasons.append("Analysis confidence is below the safe threshold.")

    requires_human_review = bool(rule_flags)
    risk_score = 0.85 if requires_human_review else 0.28
    risk_level = "high" if requires_human_review else "low"
    if not risk_reasons:
        risk_reasons.append("Position sizing and confidence are within the demo guardrails.")

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_reasons": risk_reasons,
        "rule_flags": rule_flags,
        "requires_human_review": requires_human_review,
    }
