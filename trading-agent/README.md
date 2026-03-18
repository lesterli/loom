# Sentra - Trading Agent

`Sentra` is a Python LangGraph demo that lives alongside the Rust workspace without joining it.

Phase 1 scope:

- stub `StateGraph` with mock node outputs
- low-risk and high-risk end-to-end examples
- deterministic routing
- checkpoint-enabled execution

## Quickstart

```bash
cd trading-agent
uv sync
uv run python examples/low_risk_query.py
uv run python examples/high_risk_query.py
uv run python examples/review_rejected.py
```
