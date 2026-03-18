from sentra.state import TradingState


def analyst_node(state: TradingState) -> TradingState:
    query = state.get("query", "").lower()
    is_high_risk = any(token in query for token in ("all in", "all-in", "10x", "leverage"))
    data_quality_flags = state.get("data_quality_flags", [])
    tool_errors = state.get("tool_errors", [])
    technical_data = state.get("technical_data", {})
    market_data = state.get("market_data", {})

    confidence = 0.76 if not is_high_risk else 0.49
    if data_quality_flags:
        confidence = max(0.35, confidence - 0.18)

    key_factors = [
        "Price trend captured from CoinGecko market snapshot."
        if market_data.get("source") == "coingecko"
        else "Market snapshot unavailable; analysis is degraded.",
        (
            f"Technical bias: {technical_data.get('macd_bias', 'unknown')} / "
            f"{technical_data.get('trend_bias', 'unknown')}."
        ),
    ]
    if is_high_risk:
        key_factors.append("User request implies aggressive risk appetite.")
    if tool_errors:
        key_factors.append(f"Data fetch issues: {', '.join(tool_errors)}")

    analysis = {
        "trend": "bullish" if not is_high_risk else "volatile",
        "confidence": confidence,
        "key_factors": key_factors,
        "open_questions": data_quality_flags,
        "needs_replan": False,
        "executed_steps": ["step_1", "step_2"],
    }

    plan = []
    for step in state.get("plan", []):
        updated = dict(step)
        updated["status"] = "done"
        if updated["id"] == "step_2":
            updated["notes"] = "Assessment completed by stub analyst."
        plan.append(updated)

    return {
        "analysis": analysis,
        "plan": plan,
    }
