from sentra.state import PlanStep, TradingState


def planner_node(state: TradingState) -> TradingState:
    asset = state.get("asset", "BTC")
    plan: list[PlanStep] = [
        {
            "id": "step_1",
            "objective": f"Fetch baseline market data for {asset}",
            "required_tools": ["get_price", "get_news", "get_technical"],
            "status": "done",
            "notes": "Phase 1 stub planner always emits the same baseline plan.",
        },
        {
            "id": "step_2",
            "objective": f"Assess whether {asset} setup is actionable",
            "required_tools": [],
            "status": "pending",
            "notes": "",
        },
    ]
    return {
        "plan": plan,
        "replan_count": state.get("replan_count", 0),
    }
