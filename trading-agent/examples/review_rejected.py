from sentra.graph import build_app


def main() -> None:
    app = build_app()
    config = {"configurable": {"thread_id": "phase1-review-rejected"}}
    state = {
        "query": "Should I go all in on BTC with leverage?",
        "asset": "BTC",
        "messages": [],
        "memory_summary": "",
        "user_profile": {"risk_tolerance": "aggressive"},
        "approval": "pending",
        "mock_human_decision": "rejected",
    }
    result = app.invoke(state, config=config)
    snapshot = app.get_state(config)

    print("Scenario: review_rejected")
    print(f"Recommendation: {result['recommendation']}")
    print(f"Blocked reason: {result['blocked_reason']}")
    print(f"Approval: {snapshot.values['approval']}")


if __name__ == "__main__":
    main()
