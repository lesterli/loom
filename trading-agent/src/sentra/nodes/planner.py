from sentra.fallbacks import build_fallback_plan
from sentra.llm import LLMConfigError, LLMResponseError, llm_enabled, structured_completion
from sentra.schemas import PlannerOutputSchema
from sentra.state import TradingState


def generate_plan(state: TradingState) -> tuple[list[dict], str, str | None]:
    asset = state.get("asset", "BTC")
    replan_count = state.get("replan_count", 0)

    if llm_enabled():
        system_prompt = (
            "You are a trading-agent planner. Produce a concise executable plan as JSON. "
            "Do not mention tools that are unavailable. Available tools are get_price and get_technical. "
            "Keep the plan to 2-4 steps and mark each step status as pending."
        )
        user_prompt = (
            f"User query: {state.get('query', '')}\n"
            f"Asset: {asset}\n"
            f"User profile: {state.get('user_profile', {})}\n"
            f"Memory summary: {state.get('memory_summary', '')}\n"
            f"Existing replan count: {replan_count}\n"
            "Return an executable plan tailored to this trading analysis."
        )
        try:
            parsed = structured_completion(
                PlannerOutputSchema,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            return [step.model_dump() for step in parsed.plan], "llm", None
        except (LLMConfigError, LLMResponseError, Exception) as exc:
            return build_fallback_plan(state), "fallback", str(exc)
    return build_fallback_plan(state), "fallback", None


def planner_node(state: TradingState) -> TradingState:
    replan_count = state.get("replan_count", 0)
    if state.get("plan") and state.get("analysis", {}).get("needs_replan"):
        replan_count += 1

    plan, _, _ = generate_plan(state)
    return {
        "plan": plan,
        "replan_count": replan_count,
    }
