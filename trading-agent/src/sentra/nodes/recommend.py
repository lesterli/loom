from sentra.state import TradingState


def recommend_node(state: TradingState) -> TradingState:
    strategy = state["strategy"]
    analysis = state["analysis"]
    recommendation = (
        f"{strategy['action'].upper()} {state.get('asset', 'BTC')} | "
        f"risk={state['risk_level']} ({state['risk_score']:.2f}) | "
        f"confidence={analysis['confidence']:.2f} | "
        f"thesis={strategy['thesis']}"
    )
    return {
        "recommendation": recommendation,
        "blocked_reason": "",
    }
