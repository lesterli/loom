from __future__ import annotations

import json

from sentra.fallbacks import build_fallback_analysis
from sentra.llm import LLMConfigError, LLMResponseError, llm_enabled, structured_completion
from sentra.schemas import AnalysisSchema, AnalystDecisionSchema
from sentra.state import TradingState
from sentra.tools.http import ToolDataError, ToolRequestError
from sentra.tools.market import fetch_market_chart, fetch_market_snapshot
from sentra.tools.technical import summarize_technicals


def generate_analysis(
    state: TradingState,
) -> tuple[dict, dict, dict, list[str], str, str | None]:
    supplementary_calls: list[str] = []
    tool_errors = list(state.get("tool_errors", []))
    market_data = dict(state.get("market_data", {}))
    technical_data = dict(state.get("technical_data", {}))
    fallback_error: str | None = None

    if llm_enabled():
        for _ in range(3):
            system_prompt = (
                "You are a trading analyst using a bounded ReAct loop. "
                "Choose exactly one action as structured JSON. "
                "Available actions: use_existing_data, get_market_snapshot, get_technical_summary, finalize. "
                "Only choose finalize when you can produce the final analysis object."
            )
            user_prompt = (
                f"User query: {state.get('query', '')}\n"
                f"Plan: {json.dumps(state.get('plan', []))}\n"
                f"Market data: {json.dumps(market_data, default=str)}\n"
                f"Technical data: {json.dumps(technical_data, default=str)}\n"
                f"Data quality flags: {json.dumps(state.get('data_quality_flags', []))}\n"
                f"Tool errors: {json.dumps(tool_errors)}\n"
                f"Prior supplementary calls: {json.dumps(supplementary_calls)}\n"
                "Decide the next best action."
            )
            try:
                decision = structured_completion(
                    AnalystDecisionSchema,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )
            except (LLMConfigError, LLMResponseError, Exception) as exc:
                fallback_error = str(exc)
                break

            if decision.action in {"use_existing_data", "finalize"}:
                final = decision.final_analysis
                if final is not None:
                    analysis = final.model_dump()
                    return analysis, market_data, technical_data, tool_errors, "llm", None
                else:
                    break
                break

            try:
                if decision.action == "get_market_snapshot":
                    market_data = fetch_market_snapshot(
                        state.get("asset", "BTC"),
                        coin_id=state.get("resolved_asset_id") or None,
                    )
                    supplementary_calls.append("get_market_snapshot")
                elif decision.action == "get_technical_summary":
                    market_chart = fetch_market_chart(
                        state.get("asset", "BTC"),
                        coin_id=state.get("resolved_asset_id") or None,
                    )
                    technical_data = summarize_technicals(market_chart["prices"])
                    supplementary_calls.append("get_technical_summary")
            except (ToolDataError, ToolRequestError) as exc:
                tool_errors.append(f"analyst_tool:{exc}")
        else:
            fallback_error = fallback_error or "ReAct loop exhausted without finalize action"

    analysis = build_fallback_analysis(
        {
            **state,
            "tool_errors": tool_errors,
            "market_data": market_data,
            "technical_data": technical_data,
        },
        supplementary_calls,
    )
    return analysis, market_data, technical_data, tool_errors, "fallback", fallback_error


def analyst_node(state: TradingState) -> TradingState:
    analysis, market_data, technical_data, tool_errors, _, _ = generate_analysis(state)
    plan = []
    for step in state.get("plan", []):
        updated = dict(step)
        updated["status"] = "done"
        if updated["id"] == "step_2":
            updated["notes"] = "Assessment completed by analyst."
        plan.append(updated)

    return {
        "analysis": analysis,
        "market_data": market_data,
        "technical_data": technical_data,
        "tool_errors": tool_errors,
        "plan": plan,
    }
