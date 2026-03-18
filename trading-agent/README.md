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

## Quickstart

```bash
cd trading-agent
uv sync
.venv/bin/python examples/low_risk_query.py
.venv/bin/python examples/high_risk_query.py
.venv/bin/python examples/review_rejected.py
```

## Environment

Optional:

- `COINGECKO_DEMO_API_KEY`
- `COINGECKO_PRO_API_KEY`

`Sentra` auto-loads `trading-agent/.env`, so you do not need to `source .env`
before running examples.
