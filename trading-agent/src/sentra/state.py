from typing import Any, Literal, NotRequired, TypedDict


class PlanStep(TypedDict):
    id: str
    objective: str
    required_tools: list[str]
    status: Literal["pending", "done", "failed", "skipped"]
    notes: str


class TradingState(TypedDict, total=False):
    query: str
    asset: str

    messages: list[dict[str, str]]
    memory_summary: str
    user_profile: dict[str, Any]

    plan: list[PlanStep]
    replan_count: int

    market_data: dict[str, Any]
    news_data: list[dict[str, Any]]
    onchain_data: dict[str, Any]
    technical_data: dict[str, Any]
    resolved_asset_id: str

    data_quality_flags: list[str]
    tool_errors: list[str]

    analysis: dict[str, Any]
    strategy: dict[str, Any]

    risk_score: float
    risk_level: Literal["low", "medium", "high"]
    risk_reasons: list[str]
    rule_flags: list[str]
    requires_human_review: bool

    approval: Literal["pending", "approved", "rejected"]
    approval_notes: str
    mock_human_decision: NotRequired[Literal["approved", "rejected"]]

    recommendation: str
    blocked_reason: str
