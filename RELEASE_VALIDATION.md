# Release validation - 0.1.0 / M0-FIX / M0.2

Validated on **2026-08-11** in the Windows build environment. The archive remains
an independent scaffold release; the local DevilutionX checkout and all generated
build trees are excluded from the release package.

## M0-FIX: standalone scaffold

```text
Python 3.14.5
PyTorch 2.12.1+cu126
NumPy 2.5.0
CMake 4.3.3
MSVC 19.44.35227.0
vcpkg baseline 40f3c709db80acf154ac4b17a1f83c564ebd022e
```

```text
56 Python tests passed with the full ML stack
53 Python tests passed and 1 skipped in the dev-only environment
ruff check src tests scripts: passed
mypy src/dxai: passed for 37 source files
5 JSON Schemas validated
5 static schema examples validated
1 runtime episode / 10 runtime transitions validated
7 YAML files parsed
72 local documentation links validated
3 task contracts validated
asset boundary scan passed
C++20 bridge contract: 1/1 passed in Release
Python compileall passed
ZIP path/CRC/stream validation passed
no source-tree symlinks
```

The C++ bridge contract is built with MSVC `/WX`; the previous C4244 narrowing
warning is removed. The documented Windows CTest commands consistently select the
Release configuration, and the regression test `tests/test_build_contract.py`
passes.

The project was rebuilt as
`devilutionx_ai_lab-0.1.0-py3-none-any.whl`, installed without dependencies in a
fresh virtual environment, and exercised through:

```text
dxai tasks
dxai ml-plan
dxai smoke --episodes 3 --agent heuristic --no-record
```

All three installed-package smoke episodes completed with `SUCCESS`.

## M0.1: pinned DevilutionX build baseline

The repository and commit are read from `upstream.lock.toml`:

```text
https://github.com/diasurgical/DevilutionX.git
07385842840437cc9a785b195f5b40b121eaeb1c
commit title: [Amiga] Disable broken optimizations
LICENSE.md SHA-256:
049382c17367e384c622369abbeda0cab1d65658c28611717e18afead341e586
```

The checkout is detached at the exact commit and clean. The fetch script completed
without downloading Diablo MPQs or original game assets. With the pinned vcpkg
baseline and Visual Studio 17 2022 x64:

```text
Release configure: passed
Release build: passed
Release output: build/devilutionx-vcpkg/Release/devilutionx.exe
Release CTest: 0 tests discovered
Debug configure with BUILD_TESTING=ON and DISABLE_LTO=ON: passed
Debug build including upstream test targets: passed
Debug CTest discovery: 556 test cases
Focused data-independent headless test set: 23/23 passed
devilutionx.exe --help: exit code 0
devilutionx.exe --version: exit code 0
```

The Release CTest result is intentional upstream behavior: the pinned CMake files
disable `BUILD_TESTING` for non-Debug MSVC builds when LTO is enabled. The complete
Debug matrix was not promoted to a pass because the upstream tests that require
game/fixture data are not runnable from this asset-free scaffold checkout. Their
failures are data/path prerequisites, not evidence of a completed AI integration.

## Scope boundary

This validates the standalone scaffold, mock environment, contracts, data path,
reference model, C++ adapter contract and the reproducible pinned upstream build
baseline. It does **not** validate a real DevilutionX observation/action bridge,
controlled Combat fixture, determinism gate, proprietary assets, a completed BC/R2D3
learner or a trained full-run agent.

The M0.1 scope statement above describes the pre-observation baseline. The M0.2
follow-up below adds a separate read-only observation probe; no raw engine
command API, candidate execution, IPC server or RL loop was added.

## M0.2 follow-up: first real observation

Validated on **2026-08-12** against the same pinned commit
`07385842840437cc9a785b195f5b40b121eaeb1c` and a user-owned local Diablo data
directory:

```text
Release observation probe build: passed
real observation: dxai.observation.v1
player: (79, 58)
local tiles: 121
visible entities: 0 at initial spawn
inventory entries: 6
same-seed stdout determinism: passed
missing-assets structured error: passed
raw JSON Schema registry validation: passed
Python probe client contract validation: passed
```

The identical UTF-8 stdout hash for two seed-123 runs was
`eadf3b0cb4beb8f7c8ca05c0746663de084430d95799908a24ab4b05cd531cb2`.
The M0.3 semantic-step gate and the M0.4 persistent lifecycle gate are covered
by the follow-up evidence below.

## M0.4: Real-asset acceptance gate

Validated on **2026-08-12** against the pinned DevilutionX revision
`07385842840437cc9a785b195f5b40b121eaeb1c`, a clean external Release build,
and user-owned local Diablo data. The repository contains none of those
external inputs.

```text
Health/Handshake:             passed
Reset(seed=123):              passed; position (79,58), engine_tick 0
32 same-worker Steps:         passed; step_id 0 -> 32, engine_tick 0 -> 320
PID continuity:               passed
Duplicate exactly-once:       passed; replay response byte-equivalent
Changed request-ID payload:   passed; REQUEST_ID_REUSE
Wrong-step oracle:            passed; STALE_STEP and equal control hash
Invalid-candidate oracle:     passed; INVALID_CANDIDATE and equal control hash
Stale episode/new IDs:        passed
A -> B -> A reset:            passed
Independent same-seed traces: passed; exact canonical equality
stdout/stderr purity:         passed; protocol-only stdout
Worker cleanup:               passed; old workers reaped, close idempotent
```

The 32-step canonical trace SHA-256 was
`4e906aa70e2ad64ec790074d55a15802192aae8b1508708551a65a476825d336` in both
independent runs. The A1/A2 eight-step cold-reset traces both hashed to
`92b4939801f88937fecaea40c0d172aca36b98fa0ec27cd8f0deea5b603cc33a`.
Only documented lifecycle fields were normalized; player/world state,
candidate sets, actions and engine ticks remained in the hash.

This evidence closes the M0.4 lifecycle gate only. Global M0, M0.5, rewards,
terminal semantics, replay learning, throughput and ML remain open.

## M0.5 implementation checkpoint

The repository now contains the approved M0.5 implementation: the separate
`dxai.engine_replay.v1` environment-reproducibility artifact, strict atomic
publication and loading, semantic current-candidate playback with
`REPLAY_DIVERGENCE`, a one-process-per-vector-slot manager, and observational
soak/throughput harnesses. It does not add training-trajectory fields,
rewards, terminal/truncation flags, engine events or warm reset.

The current session has no user-owned probe, Diablo data, core assets or
runtime inputs available. Accordingly the real 100-recording/1,000-playback,
10,000-Step, 1,000-episode and parallel-worker gates are **PENDING** and are
not counted as PASS. Run
[`docs/runbooks/M05_REPLAY_SOAK_THROUGHPUT.md`](docs/runbooks/M05_REPLAY_SOAK_THROUGHPUT.md)
when those inputs are available.
