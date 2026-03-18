from sentra.nodes import data_fetch as data_fetch_module
from sentra.graph import build_app


def _mock_data_fetch(monkeypatch) -> None:
    monkeypatch.setattr(data_fetch_module, "resolve_asset_id", lambda asset: "bitcoin")
    monkeypatch.setattr(
        data_fetch_module,
        "fetch_market_snapshot",
        lambda asset, coin_id=None: {
            "asset": asset,
            "coingecko_id": "bitcoin",
            "price": 70000.0,
            "source": "coingecko",
        },
    )
    monkeypatch.setattr(
        data_fetch_module,
        "fetch_market_chart",
        lambda asset, coin_id=None: {
            "coingecko_id": "bitcoin",
            "prices": [[index, 100 + index] for index in range(60)],
        },
    )


def test_low_risk_flows_directly_to_recommend(monkeypatch) -> None:
    _mock_data_fetch(monkeypatch)
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
    assert result["analysis"]["executed_steps"] == ["step_1", "step_2"]


def test_high_risk_can_be_blocked_after_mock_human_review(monkeypatch) -> None:
    _mock_data_fetch(monkeypatch)
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
    assert "oversized_position" in result["rule_flags"]
