from sentra.graph import build_app


def test_low_risk_flows_directly_to_recommend() -> None:
    app = build_app()
    config = {"configurable": {"thread_id": "test-low-risk"}}
    result = app.invoke(
        {
            "query": "Is BTC a good buy right now?",
            "asset": "BTC",
            "messages": [],
            "memory_summary": "",
            "user_profile": {"risk_tolerance": "moderate"},
            "approval": "pending",
        },
        config=config,
    )
    snapshot = app.get_state(config)

    assert result["risk_level"] == "low"
    assert result["requires_human_review"] is False
    assert "BUY BTC" in result["recommendation"]
    assert snapshot.values["recommendation"] == result["recommendation"]


def test_high_risk_can_be_blocked_after_mock_human_review() -> None:
    app = build_app()
    config = {"configurable": {"thread_id": "test-high-risk-rejected"}}
    result = app.invoke(
        {
            "query": "Should I go all in on BTC with leverage?",
            "asset": "BTC",
            "messages": [],
            "memory_summary": "",
            "user_profile": {"risk_tolerance": "aggressive"},
            "approval": "pending",
            "mock_human_decision": "rejected",
        },
        config=config,
    )
    snapshot = app.get_state(config)

    assert result["risk_level"] == "high"
    assert result["requires_human_review"] is True
    assert result["recommendation"] == "No trading recommendation issued."
    assert snapshot.values["approval"] == "rejected"
