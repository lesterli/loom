from sentra.state import TradingState


def analyst_node(state: TradingState) -> TradingState:
    query = state.get("query", "").lower()
    is_high_risk = any(token in query for token in ("all in", "all-in", "10x", "leverage"))
    analysis = {
        "trend": "bullish" if not is_high_risk else "volatile",
        "confidence": 0.76 if not is_high_risk else 0.49,
        "key_factors": [
            "Price trend is positive in mock data.",
            "Technical indicators are constructive." if not is_high_risk else "User request implies aggressive risk appetite.",
        ],
        "open_questions": [],
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
