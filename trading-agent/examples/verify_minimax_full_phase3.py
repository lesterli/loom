from __future__ import annotations

import json
import sys

from sentra.llm import default_model, llm_enabled, provider_name
from sentra.nodes.analyst import generate_analysis
from sentra.nodes.data_fetch import data_fetch_node
from sentra.nodes.planner import generate_plan
from sentra.nodes.risk_officer import assess_risk
from sentra.nodes.strategist import generate_strategy


def _print_json(title: str, payload: object) -> None:
    print(title)
    print(json.dumps(payload, indent=2, default=str))
    print()


def main() -> int:
    base_state = {
        "query": "Should I buy BTC for a short swing trade this week?",
        "asset": "BTC",
        "messages": [],
        "memory_summary": "",
        "user_profile": {"risk_tolerance": "moderate", "preferred_horizon": "swing"},
        "approval": "pending",
    }

    print("Phase 3 Full Provider Check")
    print(f"llm_enabled={llm_enabled()}")
    print(f"provider={provider_name()}")
    print(f"model={default_model()}")
    print()

    fetched_state = data_fetch_node(base_state)
    _print_json(
        "Data Fetch Summary",
        {
            "resolved_asset_id": fetched_state.get("resolved_asset_id"),
            "market_source": fetched_state.get("market_data", {}).get("source"),
            "technical_source": fetched_state.get("technical_data", {}).get("source"),
            "data_quality_flags": fetched_state.get("data_quality_flags"),
            "tool_errors": fetched_state.get("tool_errors"),
        },
    )

    planner_state = {**base_state, **fetched_state}
    plan, plan_source, plan_error = generate_plan(planner_state)
    print(f"Planner source: {plan_source}")
    if plan_error:
        print(f"Planner fallback reason: {plan_error}")
    _print_json("Planner output", plan)

    analyst_state = {**planner_state, "plan": plan}
    analysis, market_data, technical_data, tool_errors, analysis_source, analysis_error = generate_analysis(
        analyst_state
    )
    print(f"Analyst source: {analysis_source}")
    if analysis_error:
        print(f"Analyst fallback reason: {analysis_error}")
    _print_json(
        "Analyst output",
        {
            "analysis": analysis,
            "market_source": market_data.get("source"),
            "technical_source": technical_data.get("source"),
            "tool_errors": tool_errors,
        },
    )

    strategist_state = {
        **planner_state,
        "plan": plan,
        "analysis": analysis,
        "market_data": market_data,
        "technical_data": technical_data,
        "tool_errors": tool_errors,
    }
    strategy, strategy_source, strategy_error = generate_strategy(strategist_state)
    print(f"Strategist source: {strategy_source}")
    if strategy_error:
        print(f"Strategist fallback reason: {strategy_error}")
    _print_json("Strategist output", strategy)

    risk_state = {
        **strategist_state,
        "strategy": strategy,
    }
    risk_assessment, risk_source, risk_error = assess_risk(risk_state)
    print(f"Risk Officer source: {risk_source}")
    if risk_error:
        print(f"Risk Officer fallback reason: {risk_error}")
    _print_json("Risk Officer output", risk_assessment)

    sources = {
        "planner": plan_source,
        "analyst": analysis_source,
        "strategist": strategy_source,
        "risk_officer": risk_source,
    }
    _print_json("Phase 3 Source Summary", sources)

    if llm_enabled() and any(source != "llm" for source in sources.values()):
        print(
            "LLM provider is configured, but at least one Phase 3 node fell back to deterministic logic.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
