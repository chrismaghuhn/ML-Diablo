# M0.4 Persistent Environment Lifecycle Implementation Plan

> **For agentic workers:** Execute this plan task-by-task with review checkpoints. Steps use checkbox syntax for tracking. Do not commit, push, or open a pull request.

**Goal:** Turn the one-shot M0.3 DevilutionX probe into a persistent one-episode native worker with a strict JSON-lines process protocol and a Python cold-reset environment manager.

**Architecture:** Reuse the existing native M0.3 initialization, candidate generation, semantic action, advancement, and observation serialization. Add a separate `dxai.process.v1` stdio envelope and worker lifecycle state; Python replaces the worker for every Reset, so no unproven in-process global clearing is introduced. Preserve the existing Protobuf, observation schema, action space, and one-shot M0.3 behavior.

**Tech Stack:** C++23 native adapter, C++20 contract library, Python 3.11, standard-library subprocess/queue/json, pytest, CTest, JSON Schema, Ruff, mypy, pinned DevilutionX DLL.

> **Execution note (2026-08-12):** The implementation used
> `src/dxai/protocol/lifecycle.py` for the process contracts and lifecycle
> primitives, `engine_adapter/src/process_protocol.cpp` for the native
> protocol library, and `tests/test_m04_real.py` for the opt-in real gate.
> Repository-only implementation and verification tasks are complete without
> a commit. The real-asset gate remains pending because no `DXAI_M04_*` inputs
> are configured in this workspace.

---

### Task 1: Define strict Python lifecycle contracts

**Files:**
- Modify: `src/dxai/protocol/messages.py`
- Create: `src/dxai/protocol/lifecycle.py`
- Modify: `src/dxai/protocol/__init__.py`
- Test: `tests/test_protocol.py`

- [ ] Add `PROCESS_PROTOCOL_VERSION = "dxai.process.v1"`, process states, process error codes, and immutable Health/Reset/Step response models without adding reward or terminal fields.
- [ ] Add strict request builders/parsers that require exact fields and canonicalize request payloads for request fingerprints.
- [ ] Add response validators that require the expected process version, observation/action versions, state, and closed response shapes.
- [ ] Write tests first for version mismatch, unknown message type, unknown fields, missing fields, non-integer IDs, and request fingerprint equality.
- [ ] Run `python -m pytest -q tests/test_protocol.py`; confirm the new tests fail before implementing the contract models.
- [ ] Implement only the smallest contract helpers required by those tests, then rerun the focused test file.

### Task 2: Add strict UTF-8 JSON-lines framing and native-independent lifecycle primitives

**Files:**
- Modify: `src/dxai/protocol/framing.py`
- Create: `src/dxai/protocol/process.py`
- Modify: `src/dxai/protocol/__init__.py`
- Test: `tests/test_protocol.py`
- Test: `tests/test_m04_lifecycle.py`

- [ ] Set the process frame limit to exactly `1 * 1024 * 1024` bytes while retaining the old length-prefixed helpers for existing callers.
- [ ] Add one-line UTF-8 encode/decode helpers that reject malformed UTF-8, blank/multiple objects, non-JSON numeric constants, oversized bodies, and trailing bytes.
- [ ] Add a bounded request cache with 128 entries, canonical payload fingerprints, exact replay, changed-payload rejection, and high-water stale-ID rejection after eviction.
- [ ] Add a pure lifecycle state machine with `READY`, `EPISODE_ACTIVE`, and `FAULTED` transitions and pre-mutation Step validation.
- [ ] Write and run failing tests for all cache/state requirements before adding implementation.

### Task 3: Add native process-protocol library and CTest coverage

**Files:**
- Create: `engine_adapter/include/dxai_bridge/process_protocol.hpp`
- Create: `engine_adapter/src/process_protocol.cpp`
- Modify: `engine_adapter/CMakeLists.txt`
- Modify: `engine_adapter/tests/contract_test.cpp`

- [ ] Write native contract assertions first for valid/invalid UTF-8, 1 MiB maximum line handling, exact request fields, unknown-field rejection, duplicate keys, unsigned integer parsing, request-cache replay/reuse/eviction, and fault-state Step rejection.
- [ ] Run the bridge CTest target and confirm those assertions fail because the new primitives do not exist.
- [ ] Implement the bounded line reader, strict JSON request parser, response envelope helpers, request cache, and lifecycle state machine with no DevilutionX dependency.
- [ ] Add the source to the C++20 bridge contract target and rerun CTest with warnings-as-errors.

### Task 4: Refactor the native probe into `--env-stdio`

**Files:**
- Modify: `engine_adapter/observation_probe/main.cpp`
- Modify: `engine_adapter/observation_probe/CMakeLists.txt`
- Modify: `engine_adapter/include/dxai_bridge/protocol.hpp`
- Test: `tests/test_m04_native_contract.py`

- [ ] Write source-level/fixture tests first for the new mode name, explicit process version, stdout-only response shape, and unchanged M0.3 command path.
- [ ] Add the `--env-stdio` argument mode without changing the default observation or `m03` modes.
- [ ] Split M0.3 serialization so its deterministic seed-derived episode ID remains byte-compatible while environment observations accept the worker-generated lifecycle episode ID.
- [ ] Add worker startup Health handling without engine initialization, one successful Reset that initializes the existing fixture using the request seed, and one active episode only.
- [ ] Add persistent Step handling that validates all identity fields before `ClrPlrPath`/`MakePlrPath`, executes the existing native action path, accumulates engine ticks, regenerates candidates, increments `step_id` exactly once, and returns the new observation plus audit metadata.
- [ ] Add native process error responses and `FAULTED` handling for malformed/fatal protocol and native invariant failures; keep all diagnostics on stderr and flush exactly one JSON line per request to stdout.
- [ ] Add a process-unique episode ID nonce and fixed handshake constants for adapter revision, pinned DevilutionX revision, build fingerprint, supported task, and supported `MOVE_TO_TILE` feature.
- [ ] Build the probe with the existing Release configuration and run native contract tests before any real-asset gate.

### Task 5: Implement the Python persistent subprocess manager

**Files:**
- Modify: `src/dxai/env/client.py`
- Modify: `src/dxai/env/__init__.py`
- Modify: `src/dxai/env/probe.py`
- Create: `tests/test_m04_environment.py`

- [ ] Write failing fake-worker tests for Health-before-Reset, cold Reset replacement, multi-step identity updates, candidate-ID-only requests, duplicate response validation, timeout unusability, EOF/crash classification, malformed response classification, and idempotent close.
- [ ] Add a synchronous worker handle using `subprocess.Popen`, a background stdout/stderr drain, a response queue, and a bounded request deadline.
- [ ] Implement `DevilutionXEnvironment` with trusted executable/assets/core-assets/runtime configuration, fresh per-worker runtime roots, handshake validation, cold Reset, Step identity tracking, context-manager support, and cleanup.
- [ ] Ensure no Python method accepts learner-supplied paths, coordinates, raw engine commands, reward, or terminal fields.
- [ ] Map native `error_response` values to explicit Python process error codes and prevent Step after the worker is unusable.
- [ ] Run the focused Python lifecycle tests and then the full Python suite.

### Task 6: Add canonical trace utilities and M0.4 opt-in integration tests

**Files:**
- Create: `src/dxai/env/determinism.py`
- Create: `tests/test_m04_real.py`
- Create: `tests/test_m04_trace.py`
- Modify: `tests/conftest.py` only if shared helpers are needed

- [ ] Write a failing canonicalization test showing lifecycle IDs/PIDs/request IDs do not change the semantic hash while player state, engine tick, candidate semantics, or action sequence changes do.
- [ ] Implement canonical trace normalization that excludes only documented lifecycle metadata and hashes canonical JSON with SHA-256.
- [ ] Add opt-in real tests using `DXAI_M04_PROBE`, `DXAI_DIABLO_DATA`, `DXAI_DEVILUTIONX_CORE_ASSETS`, and `DXAI_DEVILUTIONX_RUNTIME` that run 32 Steps in one PID, use a deterministic semantic candidate policy, record trace hashes, and skip with an explicit external-input message when those paths are unavailable.
- [ ] Add real tests for wrong step, invalid candidate, stale episode, duplicate request exactly-once, timeout recovery, crash/EOF recovery, and A→B→A contamination.

### Task 7: Update factual contracts, runbooks, and status documents

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `PROJECT_STATUS.md`
- Modify: `docs/03_SYSTEM_ARCHITECTURE.md`
- Modify: `docs/04_DEVILUTIONX_INTEGRATION.md`
- Modify: `docs/21_MILESTONE_ACCEPTANCE.md`
- Modify: `docs/24_IMPLEMENTATION_BACKLOG.md`
- Modify: `docs/contracts/PROCESS_PROTOCOL.md`
- Modify: `docs/contracts/DETERMINISM.md`
- Modify: `docs/INDEX.md`
- Modify: `docs/runbooks/README.md`
- Create: `docs/runbooks/M04_PERSISTENT_ENVIRONMENT.md`

- [ ] Document the exact `dxai.process.v1` JSON-lines fields, 1 MiB limit, lifecycle state machine, handshake, cold-reset reference, episode/step/request identity, cache eviction, timeout/EOF policy, stdout/stderr isolation, supported action kind, and known non-goals.
- [ ] Document canonical trace normalization and explicitly exclude lifecycle metadata without normalizing game state.
- [ ] Mark only M0.4 lifecycle items complete; leave global M0, M0.5 throughput, warm reset, rewards, terminal gameplay, replay, and ML work open.
- [ ] Add exact PowerShell and Python verification commands without adding proprietary data paths or assets.

### Task 8: Verification and evidence report

**Files:**
- Modify: `docs/runbooks/M04_PERSISTENT_ENVIRONMENT.md` with actual local results only

- [ ] Run `python -m pytest -q`.
- [ ] Run schema validation, Ruff, and mypy with their repository commands.
- [ ] Run `cmake --build build\engine_adapter-vs --config Release --parallel 4` and `ctest --test-dir build\engine_adapter-vs -C Release --output-on-failure`.
- [ ] Run the M0.2 and M0.3 real gates only when the required external build/data inputs are available; otherwise record the precise unavailable-input blocker.
- [ ] Run `python scripts\check_no_assets.py` and `git diff --check`.
- [ ] Recheck `git status --short`, `git diff --stat`, branch, baseline ancestry, and pinned upstream SHA.
- [ ] Report successful real Step count, trace hashes, reset contamination hashes/result, timeout/crash behavior, all test outcomes, remaining M0 gaps, and recommended M0.5 scope. Do not commit or push.

## Execution status

Tasks 1-7 and the repository-only portion of Task 8 were implemented on
2026-08-12 without a commit. The final local evidence is 86 Python tests
passed, 4 external-input tests skipped, 2/2 native CTest targets passed,
schema/artifact and asset-boundary checks passed, Ruff and mypy passed, and
both Release targets built. The real 32-step Task 8 gate remains pending
because the four `DXAI_M04_*` external inputs are not configured.
