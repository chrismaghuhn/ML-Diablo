# M0.4 - Persistent Environment Lifecycle

M0.4 adds a persistent, one-episode native worker around the existing M0.3
semantic slice. The worker keeps the loaded DevilutionX globals, level state,
RNG state and engine tick progression alive across Steps. Python performs a
cold reset by closing that worker and starting a fresh one.

The authoritative process surface is `dxai.process.v1`: strict UTF-8 JSON
Lines, one object per line, a 1 MiB body limit, and no reward or terminal
fields. The only supported semantic action remains `MOVE_TO_TILE`; candidates
are still generated and validated by the native M0.3 path.

## Scope and lifecycle

```text
Python reset
  -> close old worker
  -> fresh runtime root and native process
  -> health_request / health_response
  -> reset_request / reset_response
  -> EPISODE_ACTIVE
       step_request / step_response ...
```

The native state machine is `READY -> EPISODE_ACTIVE`. A fatal framing,
protocol or engine invariant failure changes the worker to `FAULTED`; the
Python manager discards it. Timeout, EOF, crash or malformed response also
make the Python handle unusable. Python does not retry a timed-out Step.

Every successful Reset receives a process-unique episode ID. The initial
observation has `step_id=0`; each successful Step increments it exactly once
after native action resolution returns to the M0.3 decision boundary. A Step
contains only the lifecycle identity, expected step, candidate ID and current
candidate-set digest. Coordinates and raw engine commands are not accepted.

The worker caches 128 completed request IDs. Exact duplicates replay the
serialized response without a second mutation. Changed payloads with an old
ID are `REQUEST_ID_REUSE`; evicted old IDs are `REQUEST_ID_EXPIRED`.

## External inputs

The repository deliberately contains no DevilutionX checkout, runtime DLL,
core assets or Diablo data. Configure these user-owned paths only for a local
real run:

```powershell
$env:DXAI_M04_PROBE = 'C:\path\to\dxai_observation_probe.exe'
$env:DXAI_DIABLO_DATA = 'C:\path\to\user-owned\Diablo'
$env:DXAI_DEVILUTIONX_CORE_ASSETS = 'C:\path\to\devilutionx-build\assets'
$env:DXAI_DEVILUTIONX_RUNTIME = 'C:\path\to\devilutionx-build\Release'
```

The probe must be built against the exact revision in `upstream.lock.toml`:

```text
07385842840437cc9a785b195f5b40b121eaeb1c
```

## Direct worker smoke

With the paths above configured, the process can be driven manually. stdout
must contain only response JSON-Lines; stderr is the diagnostics channel.

```powershell
$runtime = 'C:\temp\dxai-m04-runtime'
$payload = @(
  '{"type":"health_request","protocol_version":"dxai.process.v1","request_id":1}',
  '{"type":"reset_request","protocol_version":"dxai.process.v1","request_id":2,"seed":123,"task_id":"combat.single_melee.v0"}'
) -join "`n"
$payload | & $env:DXAI_M04_PROBE `
  --assets $env:DXAI_DIABLO_DATA `
  --core-assets $env:DXAI_DEVILUTIONX_CORE_ASSETS `
  --runtime-root $runtime `
  --env-stdio
```

The expected Health compatibility values and complete field sets are defined
in [`docs/contracts/PROCESS_PROTOCOL.md`](../contracts/PROCESS_PROTOCOL.md).

## Python manager

```python
from pathlib import Path

from dxai.env.client import DevilutionXEnvironment

with DevilutionXEnvironment(
    executable=Path(r"C:\path\to\dxai_observation_probe.exe"),
    assets_path=Path(r"C:\path\to\user-owned\Diablo"),
    core_assets_path=Path(r"C:\path\to\devilutionx-build\assets"),
    engine_runtime_path=Path(r"C:\path\to\devilutionx-build\Release"),
    runtime_root=Path(r"C:\temp\dxai-m04-workers"),
) as env:
    observation = env.reset(seed=123, task_id="combat.single_melee.v0")
    for _ in range(32):
        response = env.step(observation.legal_actions[0].candidate_id)
        observation = response.observation
```

The manager validates Health before Reset, validates the returned candidate
digest against the returned observation, and performs the same check after
each Step. `close()` is idempotent and reaps the native process.

## Determinism evidence

Use `canonical_trace_sha256` from `dxai.env.determinism` for semantic trace
comparison. It removes only lifecycle metadata: request IDs, process IDs,
runtime roots, timestamps and process-launch fields. It replaces the required
unique `episode_id` with a fixed lifecycle placeholder. Seed, player/world
state, ordered candidates, semantic actions, engine ticks and step ordering
remain part of the hash.

The opt-in real gate runs at least 32 successful Steps in one PID, verifies
same-seed trace equality, rejected-step non-mutation, duplicate replay, and
A -> B -> A cold-reset isolation:

```powershell
python -m pytest -q tests\test_m04_real.py
```

If the external variables are absent, the tests skip with the exact missing
input name. A skip is not real integration evidence.

## Repository verification

Run from the repository root:

```powershell
python -m pytest -q
python scripts\validate_artifacts.py
python scripts\check_no_assets.py
python -m ruff check src tests scripts
python -m mypy src\dxai
cmake --build build\engine_adapter-vs --config Release --parallel 4
ctest --test-dir build\engine_adapter-vs -C Release --output-on-failure
cmake --build build\observation_probe-vs --config Release --parallel 4
git diff --check
```

## Local evidence

The final repository-only verification on 2026-08-12 reported:

```text
pytest:                  86 passed, 4 skipped
artifact validation:     schemas=6, examples=6, runtime_episodes=1,
                          runtime_transitions=10, yaml=7, local_links=90
asset guard:             passed
Ruff:                    passed
mypy:                    passed, 41 source files
native CTest:            2/2 passed
engine_adapter Release:  built
observation_probe Release: built
git diff --check:        passed
```

The real-asset acceptance gate passed on 2026-08-12 using external,
user-owned Diablo data, the clean pinned DevilutionX checkout and its Release
runtime. No proprietary asset or sensitive local path is stored here.

```text
Health/Handshake:             PASS
Reset(seed=123):              PASS
same-worker semantic Steps:   32 PASS, step_id 0 -> 32
worker PID continuity:        PASS
duplicate exactly-once:       PASS
changed-payload reuse:        PASS (REQUEST_ID_REUSE)
wrong-step oracle:            PASS (STALE_STEP)
invalid-candidate oracle:     PASS (INVALID_CANDIDATE)
stale episode / new IDs:      PASS
A -> B -> A reset:            PASS
same-seed independent trace:  PASS
stdout/stderr purity:         PASS
worker cleanup/reaping:       PASS
```

Canonical trace hashes, with only documented lifecycle metadata normalized:

```text
32-step trace (both independent workers):
4e906aa70e2ad64ec790074d55a15802192aae8b1508708551a65a476825d336
A1 / A2 (8 steps):
92b4939801f88937fecaea40c0d172aca36b98fa0ec27cd8f0deea5b603cc33a
```

The gate proves the M0.4 persistent lifecycle only. Rewards, terminal
semantics, warm reset, broader actions, replay learning, throughput and ML
remain outside this milestone.

## Explicit non-goals

- no reward, terminal or learner transition fields;
- no warm reset or in-process global-state clearing;
- no new action kind beyond M0.3 `MOVE_TO_TILE`;
- no parallel/vector worker manager;
- no replay database, ML training, combat damage or terminal gameplay;
- no commit, push or pull request as part of M0.4 implementation.
