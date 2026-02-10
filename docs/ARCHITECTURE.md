# agent-eval-rs Architecture

## Constraints

1. **Immutable inputs** — dataset and config versions are always traceable.
2. **Control / Execution separation** — orchestration never executes; runners never schedule.
3. **Layered scoring** — deterministic scores and LLM judge scores computed separately, then aggregated.
4. **Full-chain attribution** — every score traces back to case / attempt / trace / artifact.

## Crate Structure

```text
agent-eval-rs/
  Cargo.toml              # workspace
  eval-core/              # domain types, config, trace, error
  eval-engine/            # runner, scorer, orchestration loop
  eval-adapters/          # agent + judge adapters (feature-flagged)
  eval-cli/               # CLI entry point (clap)
  examples/               # manifest.json + profile.toml
```

### Dependency Graph

```text
eval-cli ──→ eval-engine ──→ eval-core
  │               ↑
  └──→ eval-adapters ───→ eval-core
```

### eval-core

Domain types. Zero vendor dependencies.

| Module | Responsibility |
|--------|---------------|
| `models/` | `Run`, `Case`, `Score`, `DatasetManifest`, `RunSpec` |
| `config/` | Config loading, merging, validation |
| `trace/` | `TraceEvent` enum, JSONL writer |
| `error.rs` | Domain errors (`thiserror`) |

Budget and timeout are fields on `RunSpec`, not a separate module.
Storage is plain `fs::write` to `{store_root}/runs/{run_id}/cases/{case_id}/`.

### eval-engine

Orchestration and execution. Depends only on `eval-core`.

| Module | Responsibility |
|--------|---------------|
| `runner/` | `Runner` trait, subprocess execution, artifact capture |
| `scorer/` | `Scorer` trait, deterministic scorer (`cargo check` + `cargo test`) |
| `orchestrator.rs` | Iterate cases, invoke runner + scorer, emit trace events |

MVP orchestrator is a simple loop — no state machine, no concurrency.

### eval-adapters

```toml
[features]
default = ["agent-claude", "judge-anthropic"]
agent-claude = ["reqwest"]
judge-anthropic = ["reqwest"]
```

### eval-cli

```bash
eval-cli run        --dataset manifest.json --profile run.toml
```

## Runner

subprocess via `tokio::process::Command`. Agent and cargo commands are child processes.

## Artifacts

Per case: `stdout.log`, `stderr.log`, `exit_code`, `git.diff`, `check.json`, `test.json`, `files/`.

## Tech Stack

| Purpose | Choice |
|---------|--------|
| CLI | `clap` (derive) |
| Serialization | `serde` + `serde_json` |
| Async | `tokio` |
| Process execution | `tokio::process` |
| HTTP client | `reqwest` |
| Domain errors | `thiserror` (core/engine), `anyhow` (cli only) |
