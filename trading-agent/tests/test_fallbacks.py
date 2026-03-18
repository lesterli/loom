from sentra.fallbacks import build_fallback_analysis, build_fallback_plan, build_fallback_strategy


def test_build_fallback_plan_has_two_steps() -> None:
    plan = build_fallback_plan({"asset": "BTC"})
    assert len(plan) == 2
    assert plan[0]["required_tools"] == ["get_price", "get_technical"]


def test_build_fallback_analysis_includes_tool_errors() -> None:
    analysis = build_fallback_analysis(
        {
            "query": "Should I go all in on BTC with leverage?",
            "plan": [{"id": "step_1"}, {"id": "step_2"}],
            "market_data": {"source": "unavailable"},
            "technical_data": {"macd_bias": "unknown", "trend_bias": "unknown"},
            "tool_errors": ["market down"],
            "data_quality_flags": ["market_data_unavailable"],
        }
    )
    assert analysis["trend"] == "volatile"
    assert analysis["confidence"] <= 0.49
    assert any("market down" in item for item in analysis["key_factors"])


def test_build_fallback_strategy_scales_position_for_high_risk_queries() -> None:
    strategy = build_fallback_strategy(
        {
            "query": "Should I go all in on BTC with leverage?",
            "market_data": {"price": 75000.0},
        }
    )
    assert strategy["position_size_pct"] == 40.0
