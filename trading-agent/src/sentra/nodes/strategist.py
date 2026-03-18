from sentra.state import TradingState


def strategist_node(state: TradingState) -> TradingState:
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

    return {"strategy": strategy}
