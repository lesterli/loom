from __future__ import annotations

from typing import Any

from sentra.state import PlanStep, TradingState


def build_fallback_plan(state: TradingState) -> list[PlanStep]:
    asset = state.get("asset", "BTC")
    return [
        {
            "id": "step_1",
            "objective": f"Review baseline market snapshot and technical indicators for {asset}",
            "required_tools": ["get_price", "get_technical"],
            "status": "pending",
            "notes": "Fallback plan generated without LLM.",
        },
        {
            "id": "step_2",
            "objective": f"Assess whether {asset} setup is actionable for the user query",
            "required_tools": [],
            "status": "pending",
            "notes": "",
        },
    ]


def build_fallback_analysis(state: TradingState, supplementary_calls: list[str] | None = None) -> dict[str, Any]:
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

    return {
        "trend": "bullish" if not is_high_risk else "volatile",
        "confidence": confidence,
        "key_factors": key_factors,
        "open_questions": list(data_quality_flags),
        "needs_replan": False,
        "executed_steps": [step["id"] for step in state.get("plan", [])] or ["step_1", "step_2"],
        "supplementary_calls": supplementary_calls or [],
    }


def build_fallback_strategy(state: TradingState) -> dict[str, Any]:
    query = state.get("query", "").lower()
    is_high_risk = any(token in query for token in ("all in", "all-in", "10x", "leverage"))
    market_price = float(state.get("market_data", {}).get("price") or 0.0)
    lower_entry = round(market_price * 0.995, 2) if market_price else 68000.0
    upper_entry = round(market_price * 1.005, 2) if market_price else 68800.0
    take_profit = round(market_price * 1.05, 2) if market_price else 72000.0
    stop_loss = round(market_price * 0.955, 2) if market_price else 65500.0
    strategy = {
        "action": "buy",
        "thesis": "Momentum and sentiment are supportive in the current fetched market regime.",
        "time_horizon": "swing, 3-10 days",
        "position_size_pct": 10.0,
        "entry_zone": {"low": lower_entry, "high": upper_entry},
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "invalidation": "Lose short-term support with weakening momentum.",
    }
    if is_high_risk:
        strategy["position_size_pct"] = 40.0
        strategy["thesis"] = "User asked for an aggressive trade in a volatile setup."
    return strategy


def build_rule_based_risk(state: TradingState) -> dict[str, Any]:
    strategy = state.get("strategy", {})
    analysis = state.get("analysis", {})
    data_quality_flags = state.get("data_quality_flags", [])
    technical_data = state.get("technical_data", {})
    position_size_pct = float(strategy.get("position_size_pct") or 0.0)

    rule_flags: list[str] = []
    risk_reasons: list[str] = []

    if data_quality_flags:
        rule_flags.append("partial_data")
        risk_reasons.append("Data quality is degraded, so the recommendation is less reliable.")

    if position_size_pct > 25.0:
        rule_flags.append("oversized_position")
        risk_reasons.append("Proposed position size is too large for the demo risk policy.")

    if analysis.get("confidence", 0.0) < 0.55:
        rule_flags.append("low_confidence")
        risk_reasons.append("Analysis confidence is below the safe threshold.")

    if strategy.get("action") == "buy" and not strategy.get("stop_loss"):
        rule_flags.append("missing_stop_loss")
        risk_reasons.append("Buy strategies must define a stop loss in this demo.")

    if technical_data.get("macd_bias") == "bearish" and strategy.get("action") == "buy":
        risk_reasons.append("MACD bias is bearish while the strategy still proposes a buy setup.")

    base_risk_score = 0.28
    if "low_confidence" in rule_flags:
        base_risk_score = max(base_risk_score, 0.72)
    if "oversized_position" in rule_flags:
        base_risk_score = max(base_risk_score, 0.85)
    if "partial_data" in rule_flags:
        base_risk_score = max(base_risk_score, 0.65)
    if "missing_stop_loss" in rule_flags:
        base_risk_score = max(base_risk_score, 0.8)

    if base_risk_score >= 0.7:
        risk_level = "high"
    elif base_risk_score >= 0.4:
        risk_level = "medium"
    else:
        risk_level = "low"

    if not risk_reasons:
        risk_reasons.append("Position sizing and confidence are within the demo guardrails.")

    return {
        "rule_flags": rule_flags,
        "risk_reasons": risk_reasons,
        "base_risk_score": base_risk_score,
        "risk_level": risk_level,
        "requires_human_review": bool(rule_flags or base_risk_score > 0.7),
    }
