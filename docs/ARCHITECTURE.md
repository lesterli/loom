# agent-orch Architecture

## Summary

`agent-orch` is a local orchestration layer for multi-agent coding workflows.
It does not try to replace Codex CLI, Claude Code, or the project's existing test tools.
Its job is to coordinate them into a repeatable loop:

1. prepare an isolated worktree for a task
2. ask an executor agent to make progress
3. run validation commands
4. ask a reviewer agent to inspect the resulting diff and logs
5. convert review output into structured follow-up work
6. continue until success or an explicit stop policy triggers

The core design choice is simple: one system decides what happens next, but it never writes code itself.
All code changes happen through an executor adapter in a task-specific worktree.

## Problem Statement

Today, the individual pieces already exist:

- Codex CLI can write code and run shell-driven workflows.
- Claude Code can review code changes and produce high-signal feedback.
- Git worktrees isolate concurrent tasks cleanly.
- Local scripts can watch diffs, logs, and test output.

What is missing is the glue that turns those pieces into a reliable closed loop.

Without an orchestrator, the workflow is brittle:

- agent sessions are mixed with human state
- review output is free-form and hard to feed back into the next round
- retries are ad hoc
- artifacts are scattered across terminal scrollback and temp files
- it is hard to answer basic questions such as "what happened in round 3?" or "why did this task stop?"

`agent-orch` exists to make that loop explicit, inspectable, and reproducible.

## Goals

1. Run a local execute -> validate -> review -> fix loop with minimal manual coordination.
2. Keep executor and reviewer responsibilities separate.
3. Guarantee single-writer semantics per worktree.
4. Persist enough artifacts to replay or audit every round.
5. Normalize review results into machine-readable findings and fix items.
6. Support multiple tool backends without changing orchestration logic.
7. Stay simple enough for a single-machine MVP.

## Non-Goals

1. Not a general-purpose distributed workflow engine.
2. Not a replacement for CI, code review, or issue tracking systems.
3. Not a multi-user collaborative platform.
4. Not a benchmark harness for final product evaluation.
5. Not a system where multiple agents write to the same working tree concurrently.
6. Not a prompt laboratory for optimizing model behavior in the first version.

## Design Principles

### 1. Single writer, multiple readers

At any point, exactly one executor may write to a task worktree.
Reviewers and validators can read from that worktree or from captured artifacts, but they do not mutate source.

### 2. The orchestrator owns control, not execution

The orchestrator decides the next step, records state transitions, and enforces policy.
Adapters perform side effects.

### 3. All important handoffs are structured

Terminal output and prose are useful for humans, but orchestration needs stable machine-readable records.
Review output therefore must be normalized into structured findings and fix items.

### 4. Local-first and append-only by default

The first target is a single developer machine.
Artifacts are stored locally and appended per round so failures remain debuggable.

### 5. Prefer explicit stop conditions over "let it keep trying"

Agent loops degrade quickly without strong boundaries.
Every task must define retry limits, validation gates, and terminal states.

## System Context

`agent-orch` sits above external tools and below any higher-level product workflow.

```text
human / script
      │
      ▼
agent-orch
  ├── workspace manager
  ├── executor adapter
  ├── validator adapter
  ├── reviewer adapter
  ├── review parser
  └── artifact store
      │
      ├── git worktree
      ├── codex CLI
      ├── claude code / hooks
      └── project-specific test commands
```

The orchestrator is the control plane.
Worktrees, agents, and validation commands are the execution plane.
Artifacts are the system of record between them.

## Runtime Model

The runtime model is centered on four concepts.

### Task

A task is the unit of orchestration.
It includes:

- repository root
- target branch or base commit
- task instruction
- executor configuration
- reviewer configuration
- validation profile
- stop policy

Each task maps to exactly one writable worktree at a time.

### Run

A run is one attempt to complete a task under a fixed configuration snapshot.
A task may have multiple runs if the user restarts it with different settings.

### Round

A round is one full cycle through execution, validation, review, and decision.
The round is the main accounting unit for artifacts and state transitions.

### Finding

A finding is a normalized reviewer output item.
Each finding includes severity, evidence, affected files, and a recommended fix.
Findings are then collapsed into a `fixlist.json` for the next executor round.

## High-Level Flow

```text
create task
   │
   ▼
prepare worktree
   │
   ▼
execute round N with executor
   │
   ▼
run validation profile
   │
   ▼
collect diff + logs + status
   │
   ▼
review round N with reviewer
   │
   ▼
parse findings into fix list
   │
   ├── no blocking findings and validation passes ──→ success
   │
   ├── retry budget remains ───────────────────────→ round N+1
   │
   └── retry budget exhausted / fatal error ──────→ failed or aborted
```

## Control Plane Components

### 1. Task Manager

Responsible for:

- creating task identifiers
- resolving repository root and base revision
- loading task config
- creating initial run metadata
- preventing duplicate active writers for the same task

It should reject configurations that cannot be reproduced, such as missing base refs or undefined validation commands.

### 2. Round Coordinator

Responsible for:

- moving a run from one phase to the next
- invoking adapters in the right order
- attaching artifacts to the correct round
- deciding whether the loop continues

The coordinator should be deterministic given the same task config, adapter outputs, and repository state.

### 3. Policy Engine

Responsible for:

- max round count
- max consecutive parse failures
- max consecutive no-op executor rounds
- validation gating rules
- escalation rules for human intervention
- terminal state classification

The policy engine should be strict and boring.
If the system stops, the reason should always be recorded in a structured way.

### 4. Artifact Store

Responsible for:

- durable round-level storage
- manifest generation
- content addressing or stable naming
- artifact lookup for replay and debugging

The artifact store should treat prompts, outputs, diffs, and parsed review data as first-class records.

## Data Plane Components

### 1. Workspace Manager

The workspace manager handles git worktrees and source snapshots.

Responsibilities:

- create task-specific worktrees
- ensure a clean starting point
- capture base commit, head commit, and diff
- detect dirty state before and after executor runs
- prevent multiple concurrent writers on one worktree

Recommended strategy:

- create one worktree per task, named by task id
- branch naming pattern: `task/<task-id>`
- record `base_ref`, `base_commit`, `start_commit`, and `end_commit` per round

The MVP should assume the repository already exists locally and that git is the source of truth.

### 2. Executor Adapter

The executor adapter invokes a coding agent such as Codex CLI.

Responsibilities:

- render the executor prompt from task context
- pass structured fix items from previous rounds
- run the external command in the task worktree
- capture stdout, stderr, exit code, and duration
- detect whether the round changed the repository state

Normalized output:

```json
{
  "adapter": "codex",
  "command": ["codex", "exec", "..."],
  "exit_code": 0,
  "duration_ms": 123456,
  "changed_files": ["src/lib.rs", "tests/foo.rs"],
  "head_commit": "abc123",
  "status": "completed"
}
```

The orchestrator should not depend on Codex-specific response shapes beyond this normalized contract.

### 3. Validator Adapter

The validator adapter runs deterministic checks.

Examples:

- `cargo check`
- `cargo test`
- `pytest`
- benchmark smoke tests
- formatting or lint checks when required

Responsibilities:

- execute commands in a known order
- capture output and exit status for each command
- normalize pass/fail/skipped state
- optionally short-circuit later checks when earlier gates fail

Validation must remain deterministic and tool-specific, not LLM-specific.

### 4. Reviewer Adapter

The reviewer adapter invokes a reviewer agent such as Claude Code.

Responsibilities:

- construct a review prompt from diff, validation output, and task goal
- restrict review scope to relevant artifacts
- capture stdout, stderr, exit code, and duration
- return raw review text for parsing

Key constraint:

The reviewer should not modify the task worktree.
If a review tool can run hooks or side effects, the adapter must disable write paths or run in read-only mode where possible.

### 5. Review Parser

The parser converts raw reviewer output into a structured finding set.

Responsibilities:

- extract severity
- identify evidence references
- deduplicate repeated findings
- distinguish blocking issues from suggestions
- emit stable JSON for the next executor round

If parsing fails, the raw review output is still retained and the policy engine decides whether to retry review, ask for human help, or stop.

## Canonical Data Model

The exact implementation language may change, but the logical schema should stay stable.

### TaskSpec

```json
{
  "task_id": "t_20260306_001",
  "repo_root": "/path/to/repo",
  "base_ref": "main",
  "instruction": "Implement feature X and keep tests green",
  "executor": {
    "kind": "codex",
    "profile": "default"
  },
  "reviewer": {
    "kind": "claude",
    "profile": "review-strict"
  },
  "validation_profile": "rust-default",
  "stop_policy": {
    "max_rounds": 5,
    "max_noop_rounds": 2,
    "max_parse_failures": 2
  }
}
```

### RunRecord

```json
{
  "run_id": "run_20260306_001",
  "task_id": "t_20260306_001",
  "created_at": "2026-03-06T10:00:00Z",
  "status": "running",
  "base_commit": "def456",
  "worktree_path": "/path/to/.agent-orch/worktrees/t_20260306_001"
}
```

### RoundRecord

```json
{
  "round": 2,
  "executor_status": "completed",
  "validator_status": "failed",
  "reviewer_status": "completed",
  "decision": "continue",
  "start_commit": "abc123",
  "end_commit": "abc999",
  "changed": true,
  "blocking_findings": 2,
  "suggestions": 1
}
```

### Finding

```json
{
  "id": "finding_002",
  "severity": "blocking",
  "category": "correctness",
  "summary": "The new branch skips error propagation on validation failure.",
  "evidence": [
    {
      "path": "src/orchestrator.rs",
      "line": 118
    }
  ],
  "suggested_fix": "Return the validator error and mark the round as failed."
}
```

## Filesystem Layout

Recommended local layout:

```text
.agent-orch/
  tasks/
    t_20260306_001/
      task.json
      run.json
      rounds/
        001/
          executor.prompt.md
          executor.stdout.log
          executor.stderr.log
          executor.result.json
          validation.result.json
          review.prompt.md
          review.stdout.log
          review.stderr.log
          review.result.json
          findings.json
          fixlist.json
          git.diff
          metadata.json
        002/
          ...
  worktrees/
    t_20260306_001/
```

Properties of this layout:

- task metadata is easy to inspect manually
- round boundaries are explicit
- artifacts can be archived or replayed later
- worktree paths are stable for the task lifetime

## Execution Lifecycle

### 1. Task Creation

Inputs:

- repo path
- task instruction
- selected executor and reviewer
- validation profile
- stop policy

Outputs:

- created task id
- initialized artifact directory
- reserved worktree path

### 2. Worktree Preparation

Steps:

1. resolve the base ref to a commit
2. create or reset the task branch from that commit
3. create the task worktree
4. verify the worktree is clean
5. record the initial git state

If preparation fails, the task never enters round execution.

### 3. Executor Phase

The orchestrator renders an executor prompt with:

- task instruction
- current repository status
- prior round fix list, if any
- validation policy summary
- constraints such as "write only in this worktree"

The adapter runs the executor command and records:

- command line
- environment snapshot
- exit code
- stdout and stderr
- start and end commit
- whether any files changed

No-op detection matters.
If the executor reports success but produces no diff and no commit movement across repeated rounds, the policy engine should stop instead of looping forever.

### 4. Validation Phase

Validation runs after each executor round, not only at the end.
This keeps failures close to the change that introduced them.

A validation profile is an ordered list of commands with semantics such as:

- required
- optional
- stop-on-fail
- timeout

Example profile:

```json
{
  "name": "rust-default",
  "commands": [
    {"name": "fmt", "argv": ["cargo", "fmt", "--check"], "required": true},
    {"name": "check", "argv": ["cargo", "check"], "required": true},
    {"name": "test", "argv": ["cargo", "test"], "required": true}
  ]
}
```

### 5. Review Phase

Review input should be tightly scoped.
The reviewer prompt should include only:

- task goal
- current diff
- changed files list
- validation summary
- selected log excerpts
- unresolved findings from previous rounds, if still applicable

The reviewer should not receive irrelevant repository context by default.
This improves signal and makes parsing more stable.

### 6. Parse and Decision Phase

The orchestrator parses the review into findings, computes a round decision, and writes the next fix list.

Possible decisions:

- `success`
- `continue`
- `failed_validation`
- `failed_review_parse`
- `aborted_by_policy`
- `fatal_adapter_error`
- `needs_human`

The decision record must include a human-readable reason and a machine-readable code.

## Stop Policy

The stop policy is critical because naive loops can become expensive and misleading.

Recommended default checks:

1. stop after `max_rounds`
2. stop after `max_noop_rounds`
3. stop after `max_parse_failures`
4. stop on repeated fatal validator failures that do not change across rounds
5. stop when validation passes and there are no blocking findings

Optional future policies:

- stop on budget exhaustion
- stop on token usage thresholds
- stop on repeated identical diffs
- stop on reviewer confidence below threshold

## Failure Model and Recovery

Failures should be classified, not lumped together.

### Recoverable failures

- executor command exits non-zero but worktree remains usable
- reviewer command exits non-zero
- parser fails on malformed review output
- one validation command times out

Typical response:

- persist artifacts
- mark round with failure category
- continue only if policy permits

### Non-recoverable failures

- worktree cannot be created or is corrupted
- repository base ref cannot be resolved
- adapter contract is violated
- artifact store cannot persist required state

Typical response:

- terminate the run
- mark status as fatal
- retain partial artifacts for debugging

### Human escalation

Some states should stop automation and ask for human intervention:

- repeated parser instability
- repeated executor no-op rounds
- repeated conflicting reviewer findings
- repository conflicts that require a product decision

## Concurrency Model

The MVP concurrency model should remain conservative.

Allowed:

- multiple tasks on the same machine, each with its own worktree
- parallel reviewers for different tasks
- background watchers that react to completed rounds

Disallowed:

- multiple executors writing to the same task worktree
- reviewer and executor mutating the same worktree simultaneously
- cross-task artifact directories sharing mutable files

This keeps correctness obvious and debugging tractable.

## CLI Surface

The first CLI should be small and explicit.

```bash
agent-orch task create --repo . --base main --instruction-file task.md
agent-orch run start <task-id>
agent-orch run status <task-id>
agent-orch run inspect <task-id> --round 2
agent-orch run resume <task-id>
agent-orch run abort <task-id>
```

Design notes:

- `task create` defines intent
- `run start` begins execution
- `run resume` re-enters a stopped task from persisted state
- `run inspect` is for artifact discovery, not live control

## Observability

The system should be debuggable without attaching a debugger.

Minimum observability requirements:

- event log per run
- round-level status summary
- adapter durations
- exit codes for every external command
- git commit and diff references
- stable file paths for prompts and outputs

Useful future additions:

- JSONL event stream
- terminal dashboard
- metrics export
- web viewer for round artifacts

## Security and Isolation

`agent-orch` runs untrusted or semi-trusted external tools on local code.
The architecture should assume mistakes are possible.

Basic safeguards:

- use task-specific worktrees
- minimize credentials available to child processes
- avoid handing reviewers write-capable environments
- store a minimal environment snapshot for replay
- record command lines and relevant environment overrides

The first version does not need a full sandbox, but it should make unsafe behavior visible.

## Configuration Model

Configuration should separate stable profiles from per-task overrides.

Suggested layers:

1. repo-level defaults
2. named executor/reviewer profiles
3. validation profiles
4. per-task overrides

This keeps common workflows simple while still allowing task-specific tuning.

## Recommended MVP Scope

The MVP should intentionally exclude anything that weakens the core loop.

### Include

- single-machine local execution
- git worktree management
- one executor adapter for Codex CLI
- one reviewer adapter for Claude
- one deterministic validation profile
- round artifact persistence
- structured findings and fix list generation
- resume and inspect commands

### Exclude

- distributed execution
- UI beyond CLI inspection
- parallel subtasks within one task
- automatic merge or branch submission
- advanced prompt optimization
- generalized plugin marketplaces

## Evolution Path

### Phase 1: Closed local loop

Implement one-task-at-a-time orchestration with persistent artifacts and explicit policies.

### Phase 2: Better operator ergonomics

Add watch mode, richer inspection commands, and more robust recovery tools.

### Phase 3: Multi-task scheduling

Allow several independent tasks to run concurrently on the same machine with shared queueing and capacity controls.

### Phase 4: Broader adapter ecosystem

Support alternate executors, reviewers, and validator packs without changing the core runtime model.

## Architectural Decision Summary

The key architectural decisions are:

1. use git worktrees as the isolation boundary
2. keep the orchestrator strictly separate from code-writing agents
3. make the round the primary unit of state and artifact storage
4. store raw outputs and parsed structured outputs side by side
5. enforce a single-writer policy per task
6. keep the MVP local, explicit, and recoverable

If these decisions hold, `agent-orch` can remain small while still being reliable enough to automate the coding-review-fix loop it is meant to own.
