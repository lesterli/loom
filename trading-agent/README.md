# Sentra - Trading Agent

`Sentra` is a Python LangGraph demo that lives alongside the Rust workspace without joining it.

Phase 1 scope:

- stub `StateGraph` with mock node outputs
- low-risk and high-risk end-to-end examples
- deterministic routing
- checkpoint-enabled execution

Phase 2 status:

- `data_fetch` now uses real CoinGecko data for market snapshot and price history
- technical indicators are computed locally from CoinGecko price history
- CoinGecko asset-id resolution is cached locally to reduce free-tier calls
- fetch failures degrade into `tool_errors` and `data_quality_flags`
- news is intentionally deferred to a later phase to keep the demo reliable

Phase 3 status:

- `planner`, `analyst`, `strategist`, and `risk_officer` support OpenAI-backed structured outputs
- if `OPENAI_API_KEY` is absent, Sentra falls back to deterministic heuristics so the demo still runs
- `analyst` now uses a bounded ReAct-style loop with a max of 3 supplementary tool decisions

## Quickstart

```bash
cd trading-agent
uv sync
.venv/bin/python examples/low_risk_query.py
.venv/bin/python examples/high_risk_query.py
.venv/bin/python examples/review_rejected.py
.venv/bin/python examples/verify_minimax_phase3.py
.venv/bin/python examples/verify_minimax_full_phase3.py
```

## Environment

Optional:

- `COINGECKO_DEMO_API_KEY`
- `COINGECKO_PRO_API_KEY`
- `OPENAI_API_KEY`
- `OPENAI_MODEL` (defaults to `gpt-4o-mini`)
- `OPENAI_BASE_URL` (set this for OpenAI-compatible providers such as MiniMax)

`Sentra` auto-loads `trading-agent/.env`, so you do not need to `source .env`
before running examples.

If `OPENAI_API_KEY` is present, Sentra will use OpenAI structured outputs for the
Phase 3 reasoning nodes. If it is absent, Sentra will automatically fall back to
deterministic heuristics.

## Provider Examples

OpenAI:

```bash
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o-mini
```

MiniMax OpenAI-compatible mode:

```bash
OPENAI_API_KEY=your_minimax_key
OPENAI_BASE_URL=https://api.minimax.io/v1
OPENAI_MODEL=MiniMax-M2.5
```

For MiniMax, Sentra uses the OpenAI SDK against the MiniMax-compatible chat
completions endpoint and validates the returned JSON locally with Pydantic.
