# M0.2 - First Real Observation

This runbook describes the first real DevilutionX integration slice. It is
read-only by design: the probe initializes one deterministic single-player
scenario and exports one observation. It does not submit candidates, advance
the game through an AI action, or open an IPC server.

## Scope

The probe exports:

- player position, resources, level, attributes, class, dungeon level and
  sanitized inventory;
- a bounded 11 x 11 local tile window around the player;
- visible monsters only;
- one observation-contract `WAIT` placeholder because the v1 observation
  schema requires a non-empty legal-candidate list.

The placeholder is not an action endpoint. Candidate generation and semantic
execution are M0.3 work.

## Required local inputs

The repository contains no DevilutionX source checkout, Diablo data, MPQs,
savegames or generated build assets. Keep all of these outside the repository.

The upstream checkout must be exactly the commit in `upstream.lock.toml`:

```text
07385842840437cc9a785b195f5b40b121eaeb1c
```

The probe needs three paths:

1. `DiabloDataPath`: the user-owned directory containing `DIABDAT.MPQ`.
2. `CoreAssetsPath`: the loose core assets produced by the pinned
   DevilutionX build, normally `<build>\assets`.
3. `EngineRuntimePath`: the Release directory containing
   `libdevilutionx_so.dll` and its runtime dependencies, normally
   `<build>\Release`.

The original game data and the loose DevilutionX core assets are deliberately
separate. The original MPQ is used as `BasePath`; the generated core assets
are used as `AssetsPath`.

## Windows PowerShell procedure

Build the pinned upstream checkout using the existing upstream build procedure
from `UPSTREAM_CHECKOUT.md`. Then run the probe wrapper from the repository
root:

```powershell
& .\scripts\run_observation_probe.ps1 `
  -DiabloDataPath 'C:\GOG Games\Diablo' `
  -DevilutionXCheckout 'C:\path\to\devilutionx-checkout' `
  -DevilutionXBuild 'C:\path\to\devilutionx-build'
```

If the core assets or runtime directory are not in their default build
locations, pass them explicitly:

```powershell
& .\scripts\run_observation_probe.ps1 `
  -DiabloDataPath 'C:\GOG Games\Diablo' `
  -DevilutionXCheckout 'C:\path\to\devilutionx-checkout' `
  -DevilutionXBuild 'C:\path\to\devilutionx-build' `
  -CoreAssetsPath 'C:\path\to\devilutionx-build\assets' `
  -EngineRuntimePath 'C:\path\to\devilutionx-build\Release'
```

The wrapper verifies the pinned commit, a clean checkout, the required MPQ,
the core text asset, the shared library, the observation schema version and
the probe's structured output. It builds the separate C++ probe unless
`-SkipBuild` is supplied.

## Direct Python client

After building the probe, Python can request the same read-only observation:

```python
from pathlib import Path

from dxai.env.probe import ObservationProbe

probe = ObservationProbe(
    executable=Path(r"build\observation_probe-vs\bin\Release\dxai_observation_probe.exe"),
    assets_path=Path(r"C:\GOG Games\Diablo"),
    core_assets_path=Path(r"C:\path\to\devilutionx-build\assets"),
    engine_runtime_path=Path(r"C:\path\to\devilutionx-build\Release"),
)
observation = probe.read(seed=123, task_id="combat.single_melee.v0")
observation.validate()
```

The Python client prepends the engine runtime directory to the child process
`PATH`, parses structured probe errors, rejects missing runtime libraries and
converts the result into the immutable Python observation contract.

## Expected M0.2 result

For the validated local run on 2026-08-12:

```text
schema_version: dxai.observation.v1
task_id:        combat.single_melee.v0
seed:           123
player:         (79, 58)
local_tiles:    121
entities:       0
inventory:      6
```

An empty visible-entity list is valid for this initial spawn. It does not
prove that the combat fixture or candidate execution exists yet.

## Determinism and failure gates

The current native probe was run twice with seed `123` and separate runtime
roots. The UTF-8 stdout hashes were identical:

```text
eadf3b0cb4beb8f7c8ca05c0746663de084430d95799908a24ab4b05cd531cb2
```

Seed `124` produced a different output hash. A missing Diablo data directory
returned the structured error code `ASSET_DATA_UNAVAILABLE` and did not open a
UI dialog. The raw stdout passed the local JSON Schema registry validation.

These checks cover the initial observation boundary only. Full transition
determinism, replay, candidate legality and reset isolation remain M0/M0.3
gates.

## Known upstream constraint

The pinned upstream `HeadlessMode` skips the UI but still starts level music.
The probe therefore disables music and sound immediately after enabling
`HeadlessMode`; this keeps the read-only process independent of an initialized
SDL audio device. This is an integration-process setting, not a gameplay-rule
change.

## Next gate: M0.3

M0.3 must add, in this order:

1. an engine-generated legal candidate list;
2. a candidate-ID-only request boundary;
3. execution of exactly one candidate through the existing semantic command
   path;
4. advancement to the next decision boundary;
5. a validated transition and state hash.

Python must never send mouse coordinates, raw DevilutionX command values or
target IDs outside the engine-generated candidate list.
