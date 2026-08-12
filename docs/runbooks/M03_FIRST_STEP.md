# M0.3 - First Semantic Step

This runbook describes the first action-capable DevilutionX slice. It is a
small deterministic fixture, not an IPC server or a complete environment.
The native probe exposes only adjacent, visible `MOVE_TO_TILE` candidates.
Python selects an issued `candidate_id`; it never sends coordinates, mouse
events or raw DevilutionX commands.

## Scope

The one-shot M0.3 surface is:

```text
Observation 0
  -> ordered MOVE_TO_TILE candidates
  -> candidate_id selected by Python
  -> native MakePlrPath
  -> bounded native logic ticks
  -> next controllable decision boundary
  -> Observation 1 and fresh candidates
```

The supported task is `combat.single_melee.v0`. The controlled fixture uses
seed `123`, a level-one dungeon player at `(79,58)`, and no visible entities
at the initial boundary. Both the initial and next boundary must expose at
least one supported movement candidate. There is no `WAIT` candidate in M0.3;
an empty supported set is a structured `NO_SUPPORTED_CANDIDATES` failure.

## Decision boundary

The adapter accepts a boundary only when all of the following are true:

- the player is active;
- the player is on the loaded `currlevel`;
- `PauseMode == 0`;
- the player is standing (`PM_STAND`);
- no walk path is pending (`walkpath[0] == WALK_NONE`);
- no destination action is pending (`destAction == ACTION_NONE`);
- the native future position equals the current tile, so no unprojected path
  state can affect candidate generation.

After `MakePlrPath`, the adapter executes native logic until the first
subsequent boundary satisfying the same predicate. It does not require the
requested target to be reached for the generic contract. The fixture test
additionally asserts that the selected adjacent target `(80,59)` is reached.
An `ACTION_RESOLUTION_FAILED` error means that the engine did not return to a
valid boundary within 256 native logic ticks, or that another bridge invariant
failed; it does not mean that a legal target was interrupted.

## Candidate generation and observability

The native adapter enumerates the eight neighboring tiles, restricts them to
the local observation window, and applies this sequence:

1. target and (for cardinal moves) DevilutionX `CanStep` corner tiles must be
   visible, explored, non-solid and unoccupied according to the same projected
   fields used by `dxai.observation.v1`;
2. native `CanStep(start, target)` and `PosOkPlayer(player, target)` must both
   accept the move;
3. duplicate semantic destinations are removed;
4. destinations are sorted by absolute `(x,y)` ascending;
5. dense IDs `0..N-1` are assigned after sorting.

The conservative occupancy filter includes player, monster, item and object
occupancy. This means an item or non-solid object can suppress a candidate,
but only when its tile is already visible in the observation. Cardinal corner
tiles are also required to be visible because `CanStep` reads them. Hidden or
inactive entities, hidden geometry, and pathfinding state therefore cannot
change candidate presence in this restricted slice. Python performs a focused
projection audit; it does not reproduce legality.

The canonical candidate identity is the ordered serialization of:

```text
dxai.observation.v1|dxai.action.v1|
candidate_id, kind, and every closed payload field
```

Labels and auxiliary features are descriptive and are excluded from this
identity. Its SHA-256 digest is carried by `dxai.probe.step.v1`. Before native
`MakePlrPath`, the adapter regenerates and compares the complete ordered
canonical set, including IDs and contract versions, not only the requested
integer's range.

## Native advancement path

The pinned upstream exports `game_loop(false)`, but its
`multi_handle_delta()` prelude requires network state created by `NetInit`.
M0.3 intentionally does not expand the fixture into `NetInit`, save loading or
IPC. The adapter therefore centralizes the pinned `GameLogic()` body ordering
in one function: player processing, dungeon monsters/objects/missiles/items,
lights, vision, sound, triggers, quests, redraw, `pfile_update(false)`, the
post-logic control hook, and `ClearLastSentPlayerCmd`. This is pinned-engine
integration code, not a Python or ML rules implementation.

## Local run

Keep the DevilutionX checkout, build, core assets and proprietary Diablo data
outside this repository. The checkout must be exactly:

```text
07385842840437cc9a785b195f5b40b121eaeb1c
```

Build/check the probe and retain the M0.2 default behavior:

```powershell
& .\scripts\run_observation_probe.ps1 `
  -DiabloDataPath 'C:\GOG Games\Diablo' `
  -DevilutionXCheckout 'C:\path\to\devilutionx-checkout' `
  -DevilutionXBuild 'C:\path\to\devilutionx-build'
```

The M0.3 observation request is the same executable with `--mode m03`:

```powershell
$env:PATH = 'C:\path\to\devilutionx-build\Release;' + $env:PATH
& .\build\observation_probe-vs\bin\Release\dxai_observation_probe.exe `
  --assets 'C:\GOG Games\Diablo' `
  --core-assets 'C:\path\to\devilutionx-build\assets' `
  --runtime-root 'C:\temp\dxai-m03-start' `
  --seed 123 `
  --task combat.single_melee.v0 `
  --mode m03
```

Python uses the same native executable:

```python
from pathlib import Path

from dxai.contracts.common import Vec2
from dxai.env.probe import ObservationProbe

probe = ObservationProbe(
    executable=Path(r"build\observation_probe-vs\bin\Release\dxai_observation_probe.exe"),
    assets_path=Path(r"C:\GOG Games\Diablo"),
    core_assets_path=Path(r"C:\path\to\devilutionx-build\assets"),
    engine_runtime_path=Path(r"C:\path\to\devilutionx-build\Release"),
    runtime_root=Path(r"C:\temp\dxai-m03-python"),
)
state = probe.start(seed=123, task_id="combat.single_melee.v0")
target = Vec2(state.observation.player.position.x + 1, state.observation.player.position.y + 1)
selected = next(
    action for action in state.observation.legal_actions
    if action.target_tile == target
)
step = state.step(selected.candidate_id)
```

The Python M0.3 surface is intentionally single-use. It returns the next
boundary as evidence, but it does not provide a second persistent step or a
full reset service. M0.4 adds that lifecycle in the separate
`--env-stdio`/`dxai.process.v1` surface; the M0.3 one-shot contract remains
unchanged.

## Evidence from the validated local run

The real run used seed `123`, selected semantically the adjacent target
`(80,59)` (native candidate ID `7` in the initial set), and produced:

```text
initial player:       (79,58)
initial candidates:   8
next player:          (80,59)
target reached:       true (fixture assertion only)
next step_id:         1
next engine_tick:     10
next candidates:      7
initial candidate SHA: 820a0f10cd88ee2928c2d1dff4dec16ad46a1f8654f1137edb84cdbf2cf2ad9c
next candidate SHA:    13656635816f06ab417bcde2a4491d21ed07ca521574eaec7751d6d7cde35ab7
```

Two clean seeded runs produced identical hashes for the canonical contract
outputs:

```text
initial observation: d743db9d0585aca64e059efccbcecfda3a01ce83db3067d7236658089ce21fc8
selected action:     1c18ddfe1b53e67cc6c12a668adcd2453e318161648faa17ac22ca7fde579c29
next observation:    e6214fa397d7dc45fec4adb1eeb78a0e74d85d59377d4b0b41d7a5832e4ceeb4
raw start stdout:    75aa3a326c643c6d31b41b9ba3607ffe10a2bf8fb36e61f6c23136bdcfd1f66d
raw step stdout:     6e768e65ee69af606dc3d4fd86d5d450cfb633a2c00fdb88d1c73d8d4f8829fa
```

The M0.2 no-mode stdout remained byte-identical at:

```text
eadf3b0cb4beb8f7c8ca05c0746663de084430d95799908a24ab4b05cd531cb2
```

## Verification

From the repository root:

```powershell
python -m pytest -q
python scripts\validate_artifacts.py
python -m ruff check src tests scripts
python -m mypy src\dxai
cmake --build build\engine_adapter-vs --config Release --parallel 4
ctest --test-dir build\engine_adapter-vs -C Release --output-on-failure
git diff --check
```

The real integration test is opt-in because proprietary data and the external
engine build are not repository inputs. Set these paths before running it:

```powershell
$env:DXAI_M03_PROBE = 'C:\path\to\dxai_observation_probe.exe'
$env:DXAI_DIABLO_DATA = 'C:\GOG Games\Diablo'
$env:DXAI_DEVILUTIONX_CORE_ASSETS = 'C:\path\to\devilutionx-build\assets'
$env:DXAI_DEVILUTIONX_RUNTIME = 'C:\path\to\devilutionx-build\Release'
python -m pytest -q tests\test_m03_real.py
```

## Limitations

- only `MOVE_TO_TILE` is supported;
- only eight adjacent visible destinations are considered;
- no `WAIT` fallback exists for a zero-supported-candidate state;
- no attack, item, town, loot, exploration or terminal action exists;
- the one-shot M0.3 mode has no persistent `ResetRequest`/`StepRequest` IPC;
  use the M0.4 runbook for the separate persistent worker;
- the M0.3 mode does not claim the M0.4 process protocol;
- the native fixture is controlled and asset-dependent; this is not global M0
  completion.
