from sentra.nodes.analyst import generate_analysis
from sentra.nodes.risk_officer import assess_risk


def test_generate_analysis_fallback_returns_source_and_analysis() -> None:
    analysis, market_data, technical_data, tool_errors, source, error = generate_analysis(
        {
            "query": "Is BTC a good buy right now?",
            "asset": "BTC",
            "plan": [{"id": "step_1"}, {"id": "step_2"}],
            "market_data": {"source": "coingecko"},
            "technical_data": {"source": "computed", "macd_bias": "bullish", "trend_bias": "bullish"},
            "tool_errors": [],
            "data_quality_flags": [],
        }
    )

    assert source == "fallback"
    assert error is None
    assert analysis["executed_steps"] == ["step_1", "step_2"]
    assert market_data["source"] == "coingecko"
    assert technical_data["source"] == "computed"
    assert tool_errors == []


def test_assess_risk_fallback_exposes_source() -> None:
    assessment, source, error = assess_risk(
        {
            "query": "Should I go all in on BTC with leverage?",
            "strategy": {"action": "buy", "position_size_pct": 40.0, "stop_loss": 65000.0},
            "analysis": {"confidence": 0.49},
            "technical_data": {"macd_bias": "bearish"},
            "data_quality_flags": [],
        }
    )

    assert source == "fallback"
    assert error is None
    assert assessment["risk_level"] == "high"
    assert "oversized_position" in assessment["rule_flags"]


def test_assess_risk_accepts_hold_strategy_with_null_position_size() -> None:
    assessment, source, error = assess_risk(
        {
            "query": "Should I buy BTC for a swing trade this week?",
            "strategy": {
                "action": "hold",
                "position_size_pct": None,
                "entry_zone": None,
                "take_profit": None,
                "stop_loss": None,
            },
            "analysis": {"confidence": 0.55},
            "technical_data": {"macd_bias": "bearish"},
            "data_quality_flags": [],
        }
    )

    assert source == "fallback"
    assert error is None
    assert assessment["risk_level"] in {"low", "medium"}
    assert "oversized_position" not in assessment["rule_flags"]
