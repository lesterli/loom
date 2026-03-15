# Device Capability CLI Design

Date: 2026-03-15
Status: Draft

## Goal

Build a Rust CLI that answers one question well:

- what Qwen3.5 models can this machine run?

Phase 1 is scoped to the **Qwen3.5 model family only**.
The CLI ships a built-in catalog of Qwen3.5 variants and their known artifacts.
Given the user's hardware and available backends, it ranks every catalog entry
by fit and presents a compatibility table.

Single-artifact estimation (`can this machine run this specific file?`)
is a secondary mode, not the default path.

The CLI is the source of truth for device detection, model catalog,
fit estimation, and backend-aware support decisions.

The skill layer stays thin:

- install or update the CLI
- run the right subcommand
- explain results to the user

## Principles

- Local-first. Core estimation must work without network access.
- JSON-first. Every command should support `--json`.
- Fail early. If a safe estimate is not possible, stop with a clear reason.
- Backend-aware. Fit depends on artifact plus runtime, not just parameter count.
- Inspect before estimate. Prefer real local artifacts over repo-level guesses.

## Command Surface

Current binary name:

```text
berth
```

Phase 1 commands:

```text
berth detect-hardware
berth estimate-models
berth inspect-artifact
berth doctor
```

### `detect-hardware`

Build a `DeviceProfile` from local system facts.

Example:

```bash
berth detect-hardware --json
```

Expected outputs:

- chip name and family
- total memory
- currently available memory
- memory bandwidth, when known
- CPU, GPU, and ANE facts, when known
- OS version
- power state, when available

### `inspect-artifact`

Build an `ArtifactProfile` from either a local artifact or a remote Hugging Face repo.

Examples:

```bash
berth inspect-artifact --path /models/model.gguf --json
berth inspect-artifact --hf Qwen/Qwen2.5-7B-Instruct --json
```

Rules:

- `--path` is the highest-confidence path
- `--hf` should not require downloading full weights
- Phase 1 artifact kinds: GGUF, safetensors, MLX directories

### `estimate-models`

The primary command. Two modes:

**Catalog mode (default):**

Detect hardware, then score every Qwen3.5 variant in the built-in catalog.

```bash
berth estimate-models --json
berth estimate-models --backend mlx --context 8192 --json
```

Outputs a ranked table of all Qwen3.5 catalog entries with:

- model name and variant
- quantization
- fit tier
- memory breakdown (weights + KV cache + overhead)
- risk labels

Optional filters:

- `--backend` — limit to a specific backend (default: all detected)
- `--context` — override context length (default: 4096)
- `--batch` — override batch size (default: 1)

**Single-artifact mode:**

When `--artifact` is provided, skip the catalog and estimate one specific file.

```bash
berth estimate-models \
  --artifact /models/model.gguf \
  --backend llama.cpp \
  --context 8192 \
  --json
```

Outputs:

- support status
- fit tier
- memory breakdown
- risk labels
- confidence level

### `doctor`

Check CLI and backend readiness before estimation.

Example:

```bash
berth doctor --json
```

Checks:

- CLI runs correctly
- `mlx`, `llama.cpp`, `ollama` are installed or absent
- executable paths and versions
- key runtime capabilities, when probeable

## Core Profiles

The estimator should operate on separate profiles.

### `DeviceProfile`

Represents the current machine.

Representative fields:

```text
chip_name
chip_family
os_version
memory_total_bytes
memory_available_bytes
memory_bandwidth_gbps
cpu_cores
gpu_cores
ane_cores
power_state
```

### `ModelProfile`

Represents the model architecture.

Representative fields:

```text
architecture
dense_or_moe
num_hidden_layers
hidden_size
num_attention_heads
num_key_value_heads
head_dim
max_position_embeddings
total_params
active_params
```

### `ArtifactProfile`

Represents the concrete weights the user wants to run.

Representative fields:

```text
artifact_kind
path_or_ref
file_size_bytes
quantization
tensor_dtype
shard_count
model_profile
```

### `BackendStaticProfile`

Represents what the CLI knows about a backend family.

Phase 1 backends:

- `mlx`
- `llama.cpp`
- `ollama`

Representative fields:

```text
backend_kind
supported_artifact_kinds
supports_mmap
default_kv_cache_dtype
default_runtime_overhead_bytes
```

### `BackendProbeResult`

Represents what the CLI learned from the local installation.

Representative fields:

```text
detected
version
executable_path
supports_metal
supports_mmap
supports_quantizations
resident_overhead_bytes
```

### `EffectiveBackendProfile`

Used by the estimator:

```text
EffectiveBackendProfile = BackendStaticProfile + BackendProbeResult + LocalOverride
```

## Built-in Catalog: Qwen3.5

The CLI ships a built-in catalog of Qwen3.5 model variants.
Each entry is a `CatalogEntry` containing a `ModelProfile` and
a list of known artifacts with their quantizations and expected file sizes.

Qwen3.5 is a **multimodal** family using a hybrid architecture
(Gated DeltaNet + Gated Attention, 3:1 alternating pattern).
All models are image-text-to-text. Default variants are instruction-tuned;
base variants use the `-Base` suffix. Vocab size: 248,320. Max context: 262,144 (256K).

Phase 1 Qwen3.5 variants:

```text
Dense:
  Qwen3.5-0.8B
  Qwen3.5-2B
  Qwen3.5-4B
  Qwen3.5-9B
  Qwen3.5-27B

MoE:
  Qwen3.5-35B-A3B     (256 experts, 8 active + 1 shared)
  Qwen3.5-122B-A10B   (256 experts, 8 active + 1 shared)
  Qwen3.5-397B-A17B   (512 experts, 10 active + 1 shared)
```

Each variant lists known artifact options:

```text
CatalogEntry:
  model_name
  model_profile          (architecture params: layers, heads, hidden_size, etc.)
  artifacts[]
    quantization         (e.g. Q4_K_M, Q8_0, F16, BF16)
    artifact_kind        (GGUF, safetensors, MLX)
    estimated_file_size_bytes
    hf_repo              (e.g. Qwen/Qwen3.5-8B-Instruct-GGUF)
```

The catalog is compiled into the binary. Updates require a CLI release.
This is intentional: the catalog is small, curated, and versioned.

## Built-in Chip Specs

Hardware probing via `sysctl` / `system_profiler` does not always expose
memory bandwidth or ANE core counts. The CLI ships a built-in chip spec
table as a fallback.

```text
ChipSpec:
  chip_identifier        (e.g. "Apple M4 Pro")
  memory_bandwidth_gbps
  gpu_cores
  ane_cores
  cpu_performance_cores
  cpu_efficiency_cores
```

Probed values take precedence. The chip spec table fills gaps.

Phase 1 chips:

```text
M1, M1 Pro, M1 Max, M1 Ultra
M2, M2 Pro, M2 Max, M2 Ultra
M3, M3 Pro, M3 Max, M3 Ultra
M4, M4 Pro, M4 Max, M4 Ultra
```

## Data Sources

### Hardware

Use local system probing, not browser heuristics.

Expected macOS sources:

- `sysctl`
- `system_profiler`
- `ioreg`
- `vm_stat`

### Artifacts

Order of trust:

1. local artifact inspection
2. remote structured metadata
3. built-in fallback rules

For Hugging Face, use structured metadata such as:

- `config.json`
- repository file list
- file sizes
- safetensors index files

Do not rely on free-form model cards for core estimation.

## How `estimate-models` Works

`estimate-models` is a static cost model plus a rule engine.
It is not a benchmark.

### Catalog mode flow

1. Detect hardware → `DeviceProfile` (merged with `ChipSpec` fallback).
2. Probe backends → `EffectiveBackendProfile` per detected backend.
3. For each `CatalogEntry` × each artifact × each backend:
   a. Resolve support.
   b. Estimate memory.
   c. Classify fit.
4. Rank results by fit tier, then by model size descending.
5. Output the full compatibility table.

### Single-artifact mode flow

Inputs:

- `DeviceProfile`
- `ArtifactProfile`
- `EffectiveBackendProfile`
- request settings such as context and batch size

Flow:

1. Resolve support.
   Check whether the backend can run the artifact at all.

2. Estimate resident weights.
   Prefer real artifact size over theoretical parameter math.

3. Estimate KV cache.

   Approximate formula:

   ```text
   kv_cache_bytes
     ~= layers
      * seq_len_total
      * batch
      * num_kv_heads
      * head_dim
      * 2
      * bytes_per_element
   ```

4. Add backend overhead.
   Include runtime overhead, scratch space, and backend-specific costs.

5. Add safety margin.
   Do not estimate to the byte.

6. Classify fit.

Fit tiers:

- `recommended`
- `works`
- `tight`
- `no_fit`
- `unsupported`

Support states:

- `supported`
- `unsupported`
- `unknown`

Common risk labels:

- `memory_bound`
- `context_limited`
- `backend_unsupported`
- `metadata_low_confidence`
- `mmap_unavailable`
- `swap_risk`

## Backend Policy

Backend logic should live in the CLI, not an external API.

Why:

- backend behavior is local runtime behavior
- the estimator must work offline
- results should stay reproducible
- local version and build flags matter

This does not mean "hardcode forever".
It means the CLI owns the baseline logic and then refines it with local probing.

## Default Decisions

### Catalog-first by default

The default mode answers: what Qwen3.5 models can this machine run?

The CLI iterates the built-in catalog, not a user-provided artifact.
Single-artifact mode is available via `--artifact` for power users
who want to check a specific local file.

### Process execution is the source of truth

`doctor` and backend probing should rely on:

- executable discovery
- `--version`
- small capability probes

Config directory inspection is optional enrichment, not required readiness.

### Use available memory for the main verdict

Primary fit verdicts should use:

- currently available memory
- plus a safety margin

Total memory should still be reported, but should not drive optimistic "can run now" claims.

### Fail closed on critical unknowns

Stop early when safe estimation is impossible.

Examples:

- artifact kind cannot be determined
- backend support cannot be resolved
- resident weight size cannot be bounded safely
- KV cache inputs are missing and cannot be inferred

Use a lower-confidence estimate only when conservative bounds are still possible.

## Phase Plan

### Phase 1: Qwen3.5 compatibility table

- replace demo `main.rs` with a real subcommand CLI (clap)
- implement `detect-hardware` with chip spec fallback table
- build the Qwen3.5 model catalog (compiled-in)
- implement `estimate-models` catalog mode
- implement `doctor`
- define stable JSON output schemas
- implement `inspect-artifact` (GGUF first)
- implement `estimate-models --artifact` single-artifact mode

### Phase 2 (future)

- expand catalog to other model families
- `inspect-artifact --hf` for remote repos
- interactive TUI mode
- catalog update mechanism

## Recommended Next Step

Build the smallest useful end-to-end slice:

1. `detect-hardware` — real hardware detection + chip spec fallback
2. Qwen3.5 catalog — hardcoded model profiles and artifact specs
3. `estimate-models` — iterate catalog, estimate fit, output table
