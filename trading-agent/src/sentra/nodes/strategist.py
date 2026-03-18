from sentra.state import TradingState


def strategist_node(state: TradingState) -> TradingState:
    query = state.get("query", "").lower()
    is_high_risk = any(token in query for token in ("all in", "all-in", "10x", "leverage"))
    strategy = {
        "action": "buy",
        "thesis": "Momentum and sentiment are supportive in the stub market regime.",
        "time_horizon": "swing, 3-10 days",
        "position_size_pct": 10.0,
        "entry_zone": {"low": 68000.0, "high": 68800.0},
        "take_profit": 72000.0,
        "stop_loss": 65500.0,
        "invalidation": "Lose short-term support with weakening momentum.",
    }
    if is_high_risk:
        strategy["position_size_pct"] = 40.0
        strategy["thesis"] = "User asked for an aggressive trade in a volatile setup."

    return {"strategy": strategy}
