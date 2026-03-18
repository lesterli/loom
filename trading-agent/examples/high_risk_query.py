from sentra.graph import build_app


def main() -> None:
    app = build_app()
    config = {"configurable": {"thread_id": "phase1-high-risk"}}
    state = {
        "query": "Should I go all in on BTC with leverage?",
        "asset": "BTC",
        "messages": [],
        "memory_summary": "",
        "user_profile": {"risk_tolerance": "aggressive"},
        "approval": "pending",
        "mock_human_decision": "approved",
    }
    result = app.invoke(state, config=config)
    snapshot = app.get_state(config)

    print("Scenario: high_risk_query")
    print(f"Recommendation: {result['recommendation']}")
    print(f"Risk level: {result['risk_level']}")
    print(f"Approval: {snapshot.values['approval']}")


if __name__ == "__main__":
    main()
