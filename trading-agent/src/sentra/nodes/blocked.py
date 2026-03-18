from sentra.state import TradingState


def blocked_node(state: TradingState) -> TradingState:
    blocked_reason = (
        "Human review rejected the strategy because the demo guardrails marked it as high risk."
    )
    return {
        "blocked_reason": blocked_reason,
        "recommendation": "No trading recommendation issued.",
    }
