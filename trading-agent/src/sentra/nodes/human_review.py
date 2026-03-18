from sentra.state import TradingState


def human_review_node(state: TradingState) -> TradingState:
    decision = state.get("mock_human_decision", "approved")
    notes = "Phase 1 mock human review."
    if decision == "approved":
        notes += " Reviewer approved the strategy."
    else:
        notes += " Reviewer rejected the strategy."
    return {
        "approval": decision,
        "approval_notes": notes,
    }
