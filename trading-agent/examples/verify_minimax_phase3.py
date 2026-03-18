from __future__ import annotations

import json
import sys

from sentra.fallbacks import build_fallback_analysis
from sentra.llm import default_model, llm_enabled, provider_name
from sentra.nodes.data_fetch import data_fetch_node
from sentra.nodes.planner import generate_plan
from sentra.nodes.strategist import generate_strategy


def main() -> int:
    base_state = {
        "query": "Should I buy BTC for a short swing trade this week?",
        "asset": "BTC",
        "messages": [],
        "memory_summary": "",
        "user_profile": {"risk_tolerance": "moderate", "preferred_horizon": "swing"},
        "approval": "pending",
    }

    print("Phase 3 Provider Check")
    print(f"llm_enabled={llm_enabled()}")
    print(f"provider={provider_name()}")
    print(f"model={default_model()}")
    print()

    fetched_state = data_fetch_node(base_state)
    print("Data Fetch Summary")
    print(
        json.dumps(
            {
                "resolved_asset_id": fetched_state.get("resolved_asset_id"),
                "market_source": fetched_state.get("market_data", {}).get("source"),
                "technical_source": fetched_state.get("technical_data", {}).get("source"),
                "data_quality_flags": fetched_state.get("data_quality_flags"),
                "tool_errors": fetched_state.get("tool_errors"),
            },
            indent=2,
        )
    )
    print()

    planner_state = {**base_state, **fetched_state}
    plan, plan_source, plan_error = generate_plan(planner_state)
    print(f"Planner source: {plan_source}")
    if plan_error:
        print(f"Planner fallback reason: {plan_error}")
    print(json.dumps(plan, indent=2))
    print()

    analysis = build_fallback_analysis({**planner_state, "plan": plan})
    strategist_state = {**planner_state, "plan": plan, "analysis": analysis}
    strategy, strategy_source, strategy_error = generate_strategy(strategist_state)
    print(f"Strategist source: {strategy_source}")
    if strategy_error:
        print(f"Strategist fallback reason: {strategy_error}")
    print(json.dumps(strategy, indent=2))
    print()

    if llm_enabled() and (plan_source != "llm" or strategy_source != "llm"):
        print(
            "LLM provider is configured, but at least one node fell back to deterministic logic.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
