from sentra.graph import build_app


def main() -> None:
    app = build_app()
    config = {"configurable": {"thread_id": "phase1-low-risk"}}
    state = {
        "query": "Is BTC a good buy right now?",
        "asset": "BTC",
        "messages": [],
        "memory_summary": "",
        "user_profile": {"risk_tolerance": "moderate"},
        "approval": "pending",
    }
    result = app.invoke(state, config=config)
    snapshot = app.get_state(config)

    print("Scenario: low_risk_query")
    print(f"Recommendation: {result['recommendation']}")
    print(f"Risk level: {result['risk_level']}")
    print(f"Checkpoint recommendation: {snapshot.values['recommendation']}")


if __name__ == "__main__":
    main()
