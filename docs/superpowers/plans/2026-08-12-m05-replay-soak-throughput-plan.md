# M0.5 Replay, Soak, Throughput & Process Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a registered `dxai.engine_replay.v1` evidence format, semantic replay playback, process-isolated vector environments, and reproducible M0.5 soak/benchmark harnesses without changing M0.4 semantics.

**Architecture:** Keep the existing `dxai.process.v1` worker and `DevilutionXEnvironment` authoritative. Add a pure, closed engine-replay data layer that records hashes and full semantic action payloads, a replay player that resolves actions against live candidates, a synchronous wrapper around independent environment processes, and separate diagnostics/harness code. Warm reset, rewards, terminal flags, engine events, and training replay remain out of scope.

**Tech Stack:** Python 3.11+, dataclasses, strict stdlib JSON/filesystem/process APIs, existing JSON Schema registry, pytest, Ruff, mypy, C++20 Release build, and the current M0.4 native worker.

---

## File map

The implementation uses focused files:

- `src/dxai/env/legal.py`: preserve the existing candidate-set hash while exposing one canonical semantic-action encoder.
- `src/dxai/data/engine_replay.py`: closed manifest/step types, strict parsing, hashing, atomic publication, and artifact loading.
- `src/dxai/env/replay.py`: compatibility checks, semantic candidate resolution, recording helper, playback, and first-divergence reporting.
- `src/dxai/env/vector.py`: synchronous process-slot composition and cleanup.
- `src/dxai/diagnostics/metrics.py`: quantiles, resource samples, failure counters, and machine-readable summaries.
- `scripts/m05_acceptance.py`: opt-in real recording/playback, legal-step stress, cold soak, long-worker soak, and parallel/throughput harness.
- `schemas/engine_replay_manifest.schema.json`, `schemas/engine_replay_step.schema.json`, and examples: registered closed schemas.
- `tests/test_engine_replay.py`, `tests/test_vector_environment.py`, and `tests/test_diagnostics.py`: focused unit/contract tests.
- `docs/runbooks/M05_REPLAY_SOAK_THROUGHPUT.md`: execution instructions and acceptance boundary.
- Existing status/backlog/contract/index documents: factual M0.4 cleanup and M0.5 scope/evidence links only.

The initial implementation was created without publication. The current explicit PR request authorizes commit, push, and draft-PR publication after verification.

## Task 1: Preserve and expose canonical semantic action identity

**Files:**
- Modify: `src/dxai/env/legal.py`
- Test: `tests/test_engine_replay.py`

- [x] **Step 1: Write the failing test**

Add a test that constructs two `MOVE_TO_TILE` candidates with different IDs,
labels, and feature vectors but the same closed semantic payload, and asserts
that `canonical_action_key` is equal. Add a second assertion that changing the
target tile changes the key while the existing candidate-set digest remains
byte-compatible with the M0.4 implementation.

- [x] **Step 2: Run the focused test and verify the expected failure**

Run:

```powershell
python -m pytest -q tests/test_engine_replay.py -k canonical_action_key
```

Expected: collection fails because `canonical_action_key` is not yet exported.

- [x] **Step 3: Implement the smallest helper**

Extract the current payload-field serialization into:

```python
def canonical_action_key(action: ActionCandidate) -> str:
    action.validate()
    return ";".join(
        [f"kind={action.kind.value}", *serialized_payload_fields(action)]
    )
```

Make `canonical_candidate_set_key` prepend `candidate_id=<index>;` to the
same helper output, preserving its exact existing string format and hash.

- [x] **Step 4: Run the focused test and verify it passes**

Run the same pytest command. Expected: the focused tests pass with no M0.4
candidate-set hash change.

## Task 2: Add the registered closed engine-replay schemas

**Files:**
- Create: `schemas/engine_replay_manifest.schema.json`
- Create: `schemas/engine_replay_step.schema.json`
- Create: `schemas/examples/engine_replay_manifest.example.json`
- Create: `schemas/examples/engine_replay_step.example.json`
- Modify: `scripts/validate_artifacts.py`
- Modify: `tests/test_schemas.py`

- [x] **Step 1: Write failing schema-registration tests**

Add tests that load both schemas through the existing registry, validate the
examples, reject an extra manifest field, reject an extra action field, and
reject a non-safe `steps_file`.

- [x] **Step 2: Run the tests and verify they fail for missing schemas**

Run:

```powershell
python -m pytest -q tests/test_schemas.py -k engine_replay
```

Expected: failure because the new schema files and registry example mappings
do not exist.

- [x] **Step 3: Add exact closed schemas**

Define `additionalProperties: false`, the `dxai.engine_replay.v1` and
`dxai.engine_replay_step.v1` constants, non-negative integer bounds, SHA-256
patterns, the literal `steps.jsonl`, and a shared closed semantic-action
definition with all payload slots required and null when unused.

- [x] **Step 4: Register and validate examples**

Extend `validate_examples` and `tests/test_schemas.py` mappings so the new
schemas are part of the existing central validator. Do not add a separate
schema registry.

- [x] **Step 5: Run the focused schema tests**

Run the command from Step 2. Expected: all new schema tests pass.

## Task 3: Implement strict engine-replay artifact types and atomic I/O

**Files:**
- Create: `src/dxai/data/engine_replay.py`
- Test: `tests/test_engine_replay.py`

- [x] **Step 1: Write failing validation and publication tests**

Cover:

```python
EngineReplayStep.from_dict(valid_step)
EngineReplayManifest.from_dict(valid_manifest)
publish_engine_replay(path, manifest, steps)
load_engine_replay(path)
```

Add failures for missing files, checksum mismatch, unsupported version,
unknown fields, duplicate JSON keys, NaN/Infinity, invalid action payload,
non-contiguous step IDs, path traversal, symlinked steps, and partial
artifacts. Assert that a successful publication contains only `manifest.json`
and `steps.jsonl` and that no temporary file remains.

- [x] **Step 2: Run the tests and verify the expected missing-module failure**

Run:

```powershell
python -m pytest -q tests/test_engine_replay.py
```

Expected: import failure for `dxai.data.engine_replay`.

- [x] **Step 3: Implement strict dataclasses and loaders**

Implement the exact manifest and step fields from the approved spec. Use
`json.loads` with a duplicate-key `object_pairs_hook` and a
`parse_constant` function that raises for NaN/Infinity. Check every nested
mapping against its closed field set. Reject path-like asset fingerprints and
all manifest filenames other than `steps.jsonl`.

- [x] **Step 4: Implement semantic hashes**

Use the existing canonical JSON serializer and lifecycle-aware observation
canonicalization. Hash the ordered canonical step dictionaries after removing
only `recorded_candidate_id` from the semantic trace representation.

- [x] **Step 5: Implement atomic publication**

Write into a unique sibling temporary directory, flush/fsync files, atomically
rename the step file, write/fsync/rename the manifest last, fsync the directory
where supported, and atomically rename the completed temporary directory to
the requested final path. Refuse to overwrite an existing artifact.

- [x] **Step 6: Run the focused artifact suite**

Run:

```powershell
python -m pytest -q tests/test_engine_replay.py
```

Expected: all strict validation, hashing, corruption, and atomic-publication
tests pass.

## Task 4: Implement recorder, compatibility checks, and semantic replay playback

**Files:**
- Create: `src/dxai/env/replay.py`
- Modify: `src/dxai/protocol/lifecycle.py`
- Test: `tests/test_engine_replay.py`

- [x] **Step 1: Write failing replay tests**

Use a small fake environment with changing candidate IDs but stable semantic
actions. Test that playback sends the current ID, not `recorded_candidate_id`,
and that each of these stops before the next Step:

```text
missing semantic candidate
candidate-set hash mismatch
pre-observation hash mismatch
post-observation hash mismatch
wrong manifest revision/action/observation/task identity
```

Assert `ReplayDivergence` exposes `step_id`, `component`, `expected`, and
`actual`, and that a valid replay has equal recorded/playback trace hashes.

- [x] **Step 2: Run the tests and verify the expected missing-symbol failure**

Run:

```powershell
python -m pytest -q tests/test_engine_replay.py -k playback
```

Expected: failure because the player and `REPLAY_DIVERGENCE` code are not yet
implemented.

- [x] **Step 3: Add the structured divergence code and resolver**

Add `REPLAY_DIVERGENCE` to `ProcessErrorCode`. Implement exact semantic-key
matching over the complete current `Observation.legal_actions` list, requiring
one match and using the matched current candidate ID for `env.step`.

- [x] **Step 4: Implement compatibility validation and playback**

Validate the manifest against current protocol constants, task/seed, supplied
asset fingerprint, and the worker Health identity. Reset the fresh environment,
verify initial hashes, process each step once, verify before/after hashes and
ticks, then verify final and trace hashes. Stop on the first divergence.

- [x] **Step 5: Implement recording from M0.4 responses**

Add a recorder helper that takes the initial Observation/Health and each
`PersistentStepResponse`, stores the complete semantic action payload,
records the original ID only diagnostically, and publishes through the strict
artifact writer.

- [x] **Step 6: Run replay tests and the existing M0.4 regression tests**

Run:

```powershell
python -m pytest -q tests/test_engine_replay.py tests/test_m04_environment.py tests/test_m04_trace.py
```

Expected: all new replay tests and all selected M0.4 tests pass.

## Task 5: Implement the process-isolated vector manager

**Files:**
- Create: `src/dxai/env/vector.py`
- Modify: `src/dxai/env/__init__.py`
- Test: `tests/test_vector_environment.py`

- [x] **Step 1: Write failing vector tests**

Test `reset_many`, `step_many`, distinct slot runtime roots/PIDs, request
ordering, same-seed trace equality, different-seed separation, close
idempotency, and cleanup when one slot raises during a batch.

- [x] **Step 2: Run the focused tests and verify the expected import failure**

Run:

```powershell
python -m pytest -q tests/test_vector_environment.py
```

Expected: import failure for `VectorDevilutionXEnvironment`.

- [x] **Step 3: Implement synchronous composition**

Construct one existing `DevilutionXEnvironment` per slot, deriving a distinct
`runtime_root / env-<index>` directory. Validate batch lengths, execute slots
without threads, close all slots on a partial failure, and make `close()` safe
to call repeatedly.

- [x] **Step 4: Run vector tests**

Run the focused command from Step 2. Expected: all fake-isolation and cleanup
tests pass.

## Task 6: Add resource and benchmark primitives

**Files:**
- Create: `src/dxai/diagnostics/__init__.py`
- Create: `src/dxai/diagnostics/metrics.py`
- Test: `tests/test_diagnostics.py`

- [x] **Step 1: Write failing metric tests**

Test median/p95/p99 quantiles, finite numeric validation, deterministic failure
classification, resource-sample serialization, and runtime-directory count/
size calculation.

- [x] **Step 2: Run the tests and verify missing-module failure**

Run:

```powershell
python -m pytest -q tests/test_diagnostics.py
```

Expected: import failure for `dxai.diagnostics.metrics`.

- [x] **Step 3: Implement platform-aware observational sampling**

Use `time.perf_counter_ns()` for timing. On Windows use `ctypes` process
memory/handle APIs; on POSIX use `/proc` and `resource` where available. Use
`UNAVAILABLE` rather than invented values when an API is absent. Count and size
only files below the caller-owned runtime root.

- [x] **Step 4: Implement metric aggregation**

Return machine-readable dictionaries containing sample count, warm-up count,
median, p95, p99, Steps/s, episodes/s, baseline/intermediate/final resource
samples, and structured failure counts. Do not define machine-specific pass
thresholds.

- [x] **Step 5: Run the focused diagnostics tests**

Run the command from Step 2. Expected: all metric tests pass.

## Task 7: Implement the opt-in M0.5 real-gate harness

**Files:**
- Create: `scripts/m05_acceptance.py`
- Test: `tests/test_m05_harness.py`

- [x] **Step 1: Write failing harness tests**

Test environment-variable/path validation, deterministic seed scheduling,
structured failure classification, external output layout, and the fact that
missing `DXAI_M04_PROBE`, `DXAI_DIABLO_DATA`, `DXAI_DEVILUTIONX_CORE_ASSETS`,
or `DXAI_DEVILUTIONX_RUNTIME` produces an explicit pending/skip result rather
than a PASS.

- [x] **Step 2: Run focused harness tests and verify failure**

Run:

```powershell
python -m pytest -q tests/test_m05_harness.py
```

Expected: import failure for the new harness module.

- [x] **Step 3: Implement opt-in harness modes**

Provide command-line modes for `replay`, `stress`, `soak`, `long`,
`throughput`, `parallel`, and `all`. Use the existing environment manager and
replay player. Default seed schedules are 0..99 for recording, 10 playback
repetitions per recorded artifact, 0..999 for cold soak, and a fixed RNG seed
for legal-action stress. Catch and count only known structured failures;
unexpected exceptions remain infrastructure failures.

- [x] **Step 4: Implement report publication**

Write only non-sensitive configuration and aggregate metrics to the selected
output root:

```text
m05-<run-id>/
    manifest.json
    metrics.json
```

Never include asset paths, raw observations beyond contract hashes, raw assets,
or PIDs in semantic identity. Local diagnostic PID fields may remain in the
metrics report only where explicitly labeled lifecycle diagnostics.

- [x] **Step 5: Run harness unit tests**

Run the command from Step 2. Expected: all harness tests pass. Run the script
with no external inputs and verify its exit/report explicitly says real gates
are pending.

## Task 8: Update the central validator and documentation

**Files:**
- Modify: `scripts/validate_artifacts.py`
- Modify: `docs/24_IMPLEMENTATION_BACKLOG.md`
- Modify: `README.md`
- Modify: `PROJECT_STATUS.md`
- Modify: `RELEASE_VALIDATION.md`
- Modify: `docs/04_DEVILUTIONX_INTEGRATION.md`
- Modify: `docs/15_REPRODUCIBILITY.md`
- Modify: `docs/17_PERFORMANCE_AND_SCALING.md`
- Modify: `docs/21_MILESTONE_ACCEPTANCE.md`
- Modify: `docs/contracts/DETERMINISM.md`
- Modify: `docs/contracts/REPLAY.md`
- Modify: `docs/contracts/TRAJECTORY.md`
- Modify: `docs/INDEX.md`
- Create: `docs/runbooks/M05_REPLAY_SOAK_THROUGHPUT.md`

- [x] **Step 1: Write documentation link/registry assertions**

Extend artifact validation tests to require the new examples and runbook link.
Add a text assertion that the stale backlog sentence claiming the M0.4
32-step gate is open is absent and that the M0.5 section explicitly says
reward/terminal semantics are deferred.

- [x] **Step 2: Run the documentation assertions and verify their failure**

Run:

```powershell
python -m pytest -q tests/test_schemas.py -k m05
```

Expected: failure until registry/docs are updated.

- [x] **Step 3: Update docs without changing M0.4 semantics**

Correct the stale factual wording, describe engine replay versus training
trajectory/replay, document semantic resolution and divergence, document cold
reset as reference and warm reset as deferred, and link the runbook. Keep the
known M0.4 trace and existing process protocol unchanged.

- [x] **Step 4: Run documentation and artifact validation**

Run:

```powershell
python -m pytest -q tests/test_schemas.py -k m05
python scripts/validate_artifacts.py
```

Expected: both commands pass.

## Task 9: Full repository verification and real-gate status report

**Files:**
- No new source files; inspect all changed files and working-tree artifacts.

- [x] **Step 1: Run the focused M0.5 suite**

```powershell
python -m pytest -q tests/test_engine_replay.py tests/test_vector_environment.py tests/test_diagnostics.py tests/test_m05_harness.py
```

- [x] **Step 2: Run the full Python and quality gates**

```powershell
python -m pytest -q
python scripts/validate_artifacts.py
python scripts/check_no_assets.py
python -m ruff check src tests scripts
python -m mypy src/dxai
git diff --check
```

- [x] **Step 3: Build and test native Release targets**

```powershell
cmake --build build\engine_adapter-vs --config Release --parallel 4
ctest --test-dir build\engine_adapter-vs -C Release --output-on-failure
cmake --build build\observation_probe-vs --config Release --parallel 4
```

- [ ] **Step 4: Run opt-in real tests only when all four external inputs exist**

```powershell
python -m pytest -q tests/test_m04_real.py
python scripts/m05_acceptance.py --mode all --output <external-output-root>
```

If inputs are absent, record the exact missing variable and leave all real
acceptance counts pending. Do not substitute synthetic results for real gates.

- [x] **Step 5: Inspect final scope and report honestly**

Run:

```powershell
git status --short
git diff --stat
git diff --check
```

Report baseline SHA, changed files, focused/full verification, native status,
real-gate pending/pass counts, warm-reset deferral, and remaining global M0
gaps. Do not commit, push, or open a PR.
