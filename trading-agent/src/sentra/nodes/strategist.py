from __future__ import annotations

import json

from sentra.fallbacks import build_fallback_strategy
from sentra.llm import LLMConfigError, LLMResponseError, llm_enabled, structured_completion
from sentra.schemas import StrategySchema
from sentra.state import TradingState


def generate_strategy(state: TradingState) -> tuple[dict, str, str | None]:
    if llm_enabled():
        system_prompt = (
            "You are a trading strategist. Convert the analysis into a conservative, structured strategy. "
            "If confidence is low or data quality is degraded, prefer smaller sizing or hold."
        )
        user_prompt = (
            f"User query: {state.get('query', '')}\n"
            f"User profile: {state.get('user_profile', {})}\n"
            f"Market data: {json.dumps(state.get('market_data', {}), default=str)}\n"
            f"Technical data: {json.dumps(state.get('technical_data', {}), default=str)}\n"
            f"Analysis: {json.dumps(state.get('analysis', {}), default=str)}\n"
            "Return a structured trading strategy."
        )
        try:
            parsed = structured_completion(
                StrategySchema,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            return parsed.model_dump(), "llm", None
        except (LLMConfigError, LLMResponseError, Exception) as exc:
            return build_fallback_strategy(state), "fallback", str(exc)
    return build_fallback_strategy(state), "fallback", None


def strategist_node(state: TradingState) -> TradingState:
    strategy, _, _ = generate_strategy(state)
    return {"strategy": strategy}
