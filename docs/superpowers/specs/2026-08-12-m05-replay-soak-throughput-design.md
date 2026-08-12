# M0.5 Replay, Soak, Throughput & Process Isolation Design

**Status:** approved for implementation on 2026-08-12

**Scope:** environment reproducibility evidence for the existing DevilutionX
`MOVE_TO_TILE` slice. This design does not add machine learning, reward
semantics, terminal semantics, a new native protocol, or a warm-reset path.

## Goal

M0.5 adds a versioned engine-replay artifact, safe semantic replay playback,
repeatable soak and throughput harnesses, and a synchronous process-isolated
vector manager while preserving the M0.4 `dxai.process.v1` boundary and the
M0.4 semantic trace.

## Existing authority

The native DevilutionX worker and `DevilutionXEnvironment` remain authoritative
for initialization, legal candidate generation, candidate-set identity,
action execution, lifecycle identity, request ordering, and failure handling.
The Python layer may record and compare evidence, but it must not duplicate
native legality rules or send coordinates/raw engine commands.

The existing `dxai.transition.v1`, `EpisodeRecorder`, and
`src/dxai/training/replay.py` remain training-oriented. They are not changed to
carry engine replay data because they require reward, termination,
truncation, and behavior metadata that M0.5 does not possess.

## Engine replay contract

The new closed contract is `dxai.engine_replay.v1`. It is an environment
reproducibility artifact and is never ingested as a training transition or
prioritized replay-buffer item.

An artifact is published as:

```text
replay-directory/
    manifest.json
    steps.jsonl
```

The manifest contains exactly the following identity and integrity fields:

```text
schema_version
task_id
seed
step_count
devilutionx_revision
adapter_revision
build_fingerprint
process_protocol_version
observation_version
action_version
candidate_canonicalization_version
asset_set_fingerprint
initial_observation_sha256
initial_candidate_set_sha256
final_observation_sha256
semantic_trace_sha256
steps_file
steps_file_sha256
```

`steps_file` is closed to the safe literal `steps.jsonl`. The asset fingerprint
is an opaque non-path identity supplied by the caller; absolute paths,
directory names, PIDs, runtime roots, timestamps, and proprietary data are not
accepted as replay identity.

Each JSONL step contains exactly:

```text
step_id
observation_before_sha256
candidate_set_before_sha256
action
action_canonical_key
recorded_candidate_id
observation_after_sha256
candidate_set_after_sha256
engine_tick_before
engine_tick_after
```

`action` is the complete closed semantic payload used by `ActionCandidate`:
`kind` plus all versioned payload slots (`target_entity_id`, `target_tile`,
`inventory_slot`, `equipment_slot`, `belt_slot`, `spell_id`, `store_item_id`,
and `stat_id`). It intentionally contains no candidate ID, label, or feature
vector. `recorded_candidate_id` is diagnostic only and is excluded from
semantic identity. `action_canonical_key` and candidate-set hashing use the
existing versioned payload order and exclude labels/features.

The semantic trace hash covers the ordered canonical steps, including
observation/candidate hashes, the full semantic action payload, and engine
ticks. Lifecycle metadata is not part of the trace.

## Publication and validation

Recording writes into a unique temporary artifact directory, flushes and
`fsync`s files where supported, atomically renames `steps.jsonl.tmp` to
`steps.jsonl`, writes and validates the manifest, atomically renames the
manifest last, fsyncs the directory where supported, and publishes the
completed directory atomically. A final artifact is never visible without
both files.

Loading treats artifacts as untrusted input. It rejects missing files, unsafe
or symlinked paths, path traversal, duplicate JSON keys, unknown fields,
malformed JSON, NaN/Infinity, invalid action payloads, unsupported versions,
identity mismatches, checksum mismatches, duplicate/non-contiguous steps, and
manifest count/hash mismatches.

Schema registration is centralized with the existing `schemas/` registry and
`scripts/validate_artifacts.py`. The JSON schemas and pure-Python loader must
enforce the same closed field sets.

## Replay playback

Playback follows this sequence:

```text
validate manifest identity and artifact integrity
start a fresh M0.4 worker
Health/Handshake
Reset(recorded task and seed)
verify initial observation and candidate-set hashes
for each recorded step:
    verify current pre-observation and candidate-set hashes
    resolve the full recorded semantic action against current candidates
    send only the newly resolved current candidate_id
    verify post-observation, candidate-set, and engine-tick values
verify final observation and semantic trace hashes
```

The resolver compares exact semantic keys against the complete current legal
candidate set. It never trusts `recorded_candidate_id`. A missing action,
candidate-set change, pre/post observation change, tick change, or final trace
change raises `REPLAY_DIVERGENCE` with the first step, component, expected
value, and actual value, and playback stops by default.

Compatibility is fail-closed before Step 0. The manifest must match the
current pinned DevilutionX revision, adapter/build identity, process protocol,
observation/action versions, candidate canonicalization version, task, seed,
and caller-supplied asset fingerprint.

## Process vector manager

`VectorDevilutionXEnvironment` composes N existing
`DevilutionXEnvironment` instances. Each slot has its own native worker and
runtime root. The manager exposes synchronous `reset_many`, `step_many`, and
idempotent `close`. It does not create a second protocol, share engine state,
or use threads inside an engine.

Batch failure closes all slots before re-raising a structured error, preventing
partially live workers. Tests prove distinct PIDs/runtime roots, request
isolation, same-seed parallel trace equality, different-seed separation,
partial-failure cleanup, worker-crash isolation, and close idempotency.

## Soak and benchmark evidence

The separate M0.5 harness records machine-readable `manifest.json` and
`metrics.json` under a caller-selected external output directory. It uses a
monotonic nanosecond timer and excludes documented warm-up samples.

It provides:

- 100 real replay recordings and 1,000 fresh-worker playback executions;
- deterministic random-legal `MOVE_TO_TILE` stress accumulating 10,000 valid
  Steps, resetting after structured `NO_SUPPORTED_CANDIDATES` limitations;
- 1,000 cold-reset episodes across multiple seeds;
- a persistent-worker long-step run, segmented only when the restricted
  fixture reaches its documented candidate limitation;
- startup, health, cold-reset, Step, episode, and parallel throughput samples;
- median/p95/p99 latency and Steps/s reports;
- Python/native RSS, process/handle, file-descriptor, and runtime-directory
  samples where supported;
- explicit counts for `PROCESS_TIMEOUT`, `PROCESS_EXITED`, `PROTOCOL_ERROR`,
  `ENGINE_FAULTED`, `NO_SUPPORTED_CANDIDATES`, `REPLAY_DIVERGENCE`,
  `INVALID_CANDIDATE`, `STALE_STEP`, `STALE_EPISODE`, and
  `REQUEST_ID_REUSE`.

No machine-specific throughput threshold is used as a correctness gate.
Resource analysis reports raw baseline/intermediate/final samples and flags
unreaped workers or monotonic process/handle growth without imposing a brittle
fixed RSS threshold.

## Warm reset and event/reward decision

Warm reset is deferred. The current native adapter exposes no independently
safe full teardown/reinitialize lifecycle; calling `InitializeEngine` again
would not prove that all native globals, archives, RNG state, and runtime
resources were cleared. No synthetic warm reset is implemented or benchmarked.

M0.5 does not add engine-event, reward, terminal, truncation, or outcome
semantics. Existing observation lifecycle labels remain observation diagnostics,
not a learning event contract. Authoritative event deltas and reward versioning
are deferred to the future combat milestone.

## Acceptance boundary

Repository-only unit, schema, lint, type, native build, and asset-boundary
checks are run in this session. Real replay, 10,000-Step, 1,000-episode, and
parallel-worker gates are opt-in and require external user-owned inputs. If
those inputs are absent, the harness and tests report precise skips or
structured pending status; no real-gate PASS is inferred.

M0.4's known 32-step semantic hash remains a hard regression oracle:

```text
4e906aa70e2ad64ec790074d55a15802192aae8b1508708551a65a476825d336
```

M0.5 does not redefine M0.4 or update this hash.
