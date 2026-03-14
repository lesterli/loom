# Loom Architecture

Date: 2026-03-14
Status: Draft

## Summary

`Loom` is a local-first control plane and evaluation dashboard for family learning agents on Apple Silicon.

The first target environment is:

- host: macOS on Apple Silicon
- assumed hardware: MacBook Pro M1 Pro, 16 GB unified memory
- local agent runtime: ZeroClaw
- backend stack: Rust
- deployment mode: single-machine, single-household

`Loom` is not the agent itself. ZeroClaw remains the local execution runtime.
`Loom` sits above it and provides:

- multi-user and role isolation
- task orchestration for learning flows
- review scheduling
- run trace and observability
- durable learning records
- a clean operator and developer experience for iterating on prompts, skills, and rules

## Problem

A local family learning agent is not hard to demo, but it is hard to run well over time.

The real problems are operational:

- a parent and a child should not have the same permissions
- content ingestion from textbooks and vocabulary lists needs cleanup and normalization
- practice should follow a review cadence instead of ad hoc chat
- each agent run should leave enough trace to debug bad behavior
- learning records should accumulate into a durable knowledge state
- prompts, rules, and skills should be easy to update without breaking the whole workflow

Chat interfaces solve only the last-mile interaction.
`Loom` exists to provide the control plane around a local learning agent.

## Goals

1. Run a family learning agent fully locally on Apple Silicon.
2. Use ZeroClaw as the first local execution runtime.
3. Separate parent operator permissions from child learner permissions.
4. Turn learning interactions into structured tasks and review loops.
5. Persist task runs, traces, outcomes, and learner state locally.
6. Make prompt, skill, and rule iteration observable and debuggable.
7. Stay small enough to run comfortably on an M1 Pro with 16 GB memory.

## Non-Goals

1. Not a general LMS.
2. Not a multi-tenant SaaS platform.
3. Not a replacement for ZeroClaw runtime internals.
4. Not a voice-first system in the first version.
5. Not a mobile-first product in the first version.
6. Not a broad agent marketplace or plugin ecosystem.

## Design Principles

### 1. Local-first by default

All core state lives on the machine:

- learner profiles
- task definitions
- review queues
- run traces
- artifacts
- dashboard data

Cloud dependencies should be optional and explicit.

### 2. ZeroClaw is execution, Loom is control

ZeroClaw handles local agent execution.
`Loom` handles orchestration, storage, and observability.

This keeps the boundary clean:

- ZeroClaw decides how to run an agent
- Loom decides when, why, and under what policy an agent run should happen

### 3. Family workflows need explicit roles

The system must distinguish at least:

- parent/operator
- child/learner
- system agent

The parent configures policy.
The child triggers or responds to tasks.
The agent executes within the configured boundary.

### 4. Learning state is not chat history

A family learning system cannot rely on raw conversation logs alone.
Important state must be normalized:

- vocabulary mastery
- recent mistakes
- review due dates
- practice history
- agent version and rule version used for each run

### 5. Every automation should be inspectable

If the system generates a bad exercise, grades incorrectly, or schedules poor review tasks, the parent must be able to inspect:

- the input artifact
- the task selection
- the runtime configuration
- the model output
- the scoring result

## System Context

```text
parent / child UI
        │
        ▼
      Loom
  ├── API server
  ├── policy engine
  ├── scheduler
  ├── task planner
  ├── trace recorder
  ├── learning state store
  └── dashboard backend
        │
        ▼
   ZeroClaw runtime
  ├── local model provider
  ├── tools
  ├── channels
  └── sandbox
        │
        ▼
  local files / sqlite / imported materials
```

## Primary Use Cases

### 1. Child practice session

The child opens a simple interface and receives one task at a time, for example:

- use a word in a sentence
- solve one arithmetic problem
- answer one reading comprehension question

`Loom` records the task, result, score, and next review due date.

### 2. Parent control and review

The parent can:

- create or edit learner profiles
- import source material
- inspect daily and weekly progress
- review traces of bad runs
- tune rules, prompts, or skills

### 3. Material ingestion

The parent uploads or pastes:

- textbook vocabulary
- worksheet questions
- teacher notes
- screenshots or OCR output

`Loom` normalizes these into structured learning items.

### 4. Scheduled review

The system selects due items and generates a daily queue based on:

- last performance
- content type
- difficulty
- recency
- configured review policy

## High-Level Architecture

## 1. Frontend

Initial UI can be a thin local web app.

Main surfaces:

- learner session view
- parent dashboard
- trace inspector
- content import page
- settings and policy page

The frontend should remain replaceable.
The architecture assumes a stable Rust API backend first.

## 2. Rust Backend

The Rust backend is the system core.

Main responsibilities:

- expose local HTTP API
- manage learner and task state
- schedule review jobs
- call ZeroClaw through a stable adapter boundary
- persist runs and artifacts
- aggregate dashboard views

Candidate stack:

- HTTP: `axum`
- async runtime: `tokio`
- storage: `sqlite` via `sqlx` or `rusqlite`
- serialization: `serde`
- tracing: `tracing`

## 3. ZeroClaw Adapter

`Loom` should not couple itself directly to ZeroClaw internals.
Instead, define a small adapter interface such as:

- submit task
- run agent session
- fetch execution result
- collect runtime metadata
- surface tool and model configuration

This allows later support for:

- a mocked local executor for tests
- a non-ZeroClaw runtime
- offline replay of runs without invoking the agent

## 4. Local Data Plane

All durable state lives locally.

Recommended split:

- SQLite for normalized operational data
- filesystem for bulky artifacts

SQLite stores:

- learners
- profiles
- tasks
- runs
- scores
- review queue
- policies
- imported content metadata

Filesystem stores:

- raw imports
- OCR text
- run transcripts
- trace payloads
- snapshots of prompts and skill configs

## Core Components

### 1. Identity and Role Manager

Tracks local users and effective permissions.

Minimum roles:

- `parent_admin`
- `learner`
- `system`

Responsibilities:

- enforce visibility boundaries
- map channels to learner identities
- keep parent-only settings hidden from learner-facing views

### 2. Learner Profile Service

Stores structured learner information:

- age / grade
- subjects
- difficulty band
- vocabulary level
- channel bindings
- task preferences
- pacing constraints

This service provides context to both the scheduler and the agent runtime.

### 3. Content Ingestion Pipeline

Transforms raw material into structured items.

Stages:

1. ingest raw text or image-derived text
2. normalize and deduplicate
3. classify by subject and type
4. convert into learning items
5. attach source metadata

Examples:

- `received` -> `receive`
- repeated vocabulary collapsed into one canonical item
- worksheet questions converted into atomic practice items

### 4. Task Planner

Creates concrete practice tasks from learner state plus available content.

Examples:

- sentence-building task from vocabulary item
- single arithmetic question from math pool
- follow-up question on a recently missed concept

The planner should prefer one atomic task at a time for young learners.

### 5. Review Scheduler

Determines what should be practiced today.

Inputs:

- historical performance
- last reviewed timestamp
- item difficulty
- subject quotas
- parent policy

Outputs:

- ordered daily review queue
- next due date per learning item

The first version can use a simple spaced-review policy:

- wrong -> return soon
- partially correct -> moderate interval
- correct -> longer interval

### 6. ZeroClaw Execution Service

Executes planned tasks through ZeroClaw.

Responsibilities:

- assemble runtime context
- attach learner-safe rules
- invoke ZeroClaw
- capture agent output
- enforce timeouts and guardrails

The service should pass only the minimum required context into each run.

### 7. Scoring and Feedback Service

Post-processes the agent result.

Responsibilities:

- assign structured scores
- generate learner-friendly feedback
- record mistakes and hints
- emit parent-visible diagnostics

This layer is important because “agent output” and “learning outcome” are not the same thing.

### 8. Trace Recorder

Captures structured execution traces.

A trace record should include:

- learner id
- task id
- source item id
- runtime version
- rule version
- prompt snapshot id
- timestamps
- latency
- raw output
- normalized score
- follow-up scheduling decision

### 9. Dashboard Aggregator

Builds read models for UI pages.

Examples:

- today’s completed tasks
- streak summary
- vocabulary mastery chart
- error hotspots
- runtime latency by task type
- low-quality agent runs needing parent review

## Runtime Flow

### Practice Flow

```text
parent imports content
   │
   ▼
ingestion pipeline normalizes items
   │
   ▼
review scheduler builds learner queue
   │
   ▼
task planner creates one atomic task
   │
   ▼
ZeroClaw adapter executes task
   │
   ▼
scoring service evaluates outcome
   │
   ▼
trace recorder persists artifacts
   │
   ▼
review scheduler updates next due date
   │
   ▼
dashboard reflects new state
```

### Parent Tuning Flow

```text
parent inspects bad run
   │
   ▼
trace view shows input, config, output, score
   │
   ▼
parent edits policy / prompt / skill binding
   │
   ▼
next runs carry new version metadata
```

## Data Model

Initial core entities:

- `Learner`
- `ChannelBinding`
- `LearningItem`
- `TaskTemplate`
- `TaskRun`
- `TaskScore`
- `ReviewState`
- `PolicyConfig`
- `TraceArtifact`
- `PromptVersion`
- `SkillVersion`

Key relationships:

- one learner has many learning items
- one learning item has many task runs
- one task run has one trace bundle
- one learner has one active review state per item

## API Surface

Suggested local API groups:

- `POST /learners`
- `GET /learners/:id`
- `POST /imports`
- `POST /planner/generate`
- `POST /runs`
- `GET /runs/:id`
- `GET /learners/:id/dashboard`
- `GET /learners/:id/review-queue`
- `POST /policies/:id`
- `GET /traces/:id`

The API should be local-only in the first version unless explicitly enabled.

## Apple Silicon Constraints

For M1 Pro with 16 GB unified memory, the architecture should assume:

- one active local agent session at a time
- compact models or remote provider fallback
- bounded artifact retention
- no heavy concurrent OCR, indexing, and agent execution together

Operational guidance:

- keep runtime memory budgets explicit
- serialize expensive jobs
- store artifacts incrementally instead of loading them all into memory
- prefer one-task execution over batch generation

## Security and Safety

Even on a single machine, family workflows need boundaries.

Minimum safeguards:

- learner-facing runs use restricted tool access
- parent configuration views are not exposed in learner UI
- imported materials are treated as untrusted input
- all agent actions are logged with trace ids
- local data is stored under a dedicated app directory

Because the system is child-facing, the response style policy should also be explicit:

- no shaming language
- concise corrective feedback
- no unsafe external browsing in learner runs by default

## Observability

The first version does not need a full distributed tracing stack, but it does need strong local observability.

Required signals:

- task latency
- runtime success/failure
- scoring distribution
- ingestion error count
- queue size
- review completion rate

Recommended implementation:

- structured logs with `tracing`
- per-run JSON trace bundle
- lightweight dashboard summaries from SQLite

## Extensibility

The design should keep three boundaries stable:

### 1. Runtime boundary

ZeroClaw is first, not forever.
Use an adapter trait so the rest of the system does not depend on one runtime.

### 2. Scoring boundary

Different subjects may need different evaluators.
Math and vocabulary scoring should plug into a common interface.

### 3. Ingestion boundary

Text import comes first, image/OCR later.
Both should feed the same normalized learning item model.

## MVP Scope

The MVP should be intentionally narrow.

Included:

- one parent
- one learner
- local web API
- SQLite storage
- text-based content import
- English vocabulary sentence tasks
- single-question math tasks
- simple spaced review policy
- ZeroClaw runtime adapter
- basic run trace and dashboard

Deferred:

- voice input
- multi-device sync
- real-time collaborative channels
- advanced OCR pipeline
- multiple learners with household-wide policy inheritance
- mobile app

## Phased Build Plan

### Phase 1: Local Core

- Rust API server
- SQLite schema
- learner profile CRUD
- content import and normalization
- basic task planning

### Phase 2: Runtime Integration

- ZeroClaw adapter
- task execution
- scoring and trace persistence

### Phase 3: Review Loop

- review scheduler
- dashboard summaries
- parent inspection flows

### Phase 4: DX Hardening

- prompt/version snapshots
- run replay
- better trace inspection
- config validation

## Open Questions

1. Should ZeroClaw be embedded as a library or called as an external process first?
2. What is the smallest stable adapter contract we can define without leaking runtime internals?
3. How much scoring should be rule-based versus model-based in the MVP?
4. Should prompt and skill configs live in filesystem snapshots, SQLite, or both?
5. What is the exact local UI stack for the first parent dashboard?

## One-Line Definition

`Loom` is the local control plane around a family learning agent: it decides what to practice, who can see what, how runs are traced, and how learning state accumulates over time.
