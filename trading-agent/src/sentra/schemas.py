from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PlanStepSchema(BaseModel):
    id: str
    objective: str
    required_tools: list[str] = Field(default_factory=list)
    status: Literal["pending", "done", "failed", "skipped"] = "pending"
    notes: str = ""


class PlannerOutputSchema(BaseModel):
    plan: list[PlanStepSchema]


class AnalysisSchema(BaseModel):
    trend: Literal["bullish", "bearish", "neutral", "volatile"]
    confidence: float = Field(ge=0.0, le=1.0)
    key_factors: list[str]
    open_questions: list[str]
    needs_replan: bool = False
    executed_steps: list[str]
    supplementary_calls: list[str] = Field(default_factory=list)


class AnalystDecisionSchema(BaseModel):
    thought: str
    action: Literal["use_existing_data", "get_market_snapshot", "get_technical_summary", "finalize"]
    reason: str
    final_analysis: AnalysisSchema | None = None


class EntryZoneSchema(BaseModel):
    low: float
    high: float


class StrategySchema(BaseModel):
    action: Literal["buy", "sell", "hold"]
    thesis: str
    time_horizon: str
    position_size_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    entry_zone: EntryZoneSchema | None = None
    take_profit: float | None = None
    stop_loss: float | None = None
    invalidation: str


class RiskAssessmentSchema(BaseModel):
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_level: Literal["low", "medium", "high"]
    risk_reasons: list[str]
