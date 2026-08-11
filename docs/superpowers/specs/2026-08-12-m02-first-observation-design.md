# M0.2 First Real Observation — Design Specification

Status: approved by the explicit M0.2 implementation request

## Goal

M0.2 shall prove the first real read-only observation boundary against DevilutionX commit `07385842840437cc9a785b195f5b40b121eaeb1c`.

The probe must start without a UI, load user-provided Diablo data, initialize one deterministic single-player game state, and emit one `dxai.observation.v1` JSON observation that Python can validate.

The observation slice contains:

- the player position and core resources;
- visible monsters only;
- a bounded relative tile window with visibility/exploration filtering;
- player-observable inventory, belt, and equipment slots;
- no action execution, candidate generation, RL, or replay training.

## Non-goals

- no `reset/step` IPC server;
- no Candidate Action API and no engine command submission;
- no combat fixture mutation beyond the engine's normal initialization path;
- no pixel capture;
- no broad item valuation, shop state, or loot policy;
- no copying of DevilutionX source, Diablo data, MPQs, saves, or generated assets into this repository;
- no hard-coded machine-specific asset path.

## Alternatives considered

### A — External probe linked to the pinned upstream build (chosen)

Build the upstream checkout with its existing testing/shared-library boundary, then compile a repository-owned probe against the resulting exported library. The probe receives paths and seed as arguments, reads the initialized engine state, serializes JSON to stdout, and exits.

Advantages:

- the public repository contains only the probe and build orchestration, not upstream or proprietary assets;
- the observation boundary is explicit and easy to replace with a future process protocol;
- the first integration can remain read-only and one-shot;
- the exact upstream commit and build fingerprint can be checked before execution.

Trade-off: the probe must track the exported symbols and headers of the pinned upstream commit.

### B — Add a probe target directly to the upstream CMake tree

Patch the external upstream checkout with an additional executable target and build it as part of DevilutionX.

Advantages: direct access to upstream CMake targets and compile definitions.

Trade-offs: a larger upstream patch surface, more difficult patch application, and higher risk that integration changes are mistaken for upstream behavior.

### C — Launch the normal DevilutionX executable and scrape state

Advantages: minimal compile integration.

Trade-offs: UI/input automation, no stable state boundary, no reliable visibility semantics, and immediate violation of the semantic engine-authority design.

Approach A is selected for M0.2. Approach B remains available if the shared-library export boundary proves insufficient; that would be a separately documented compatibility decision.

## Boundary and data flow

```text
user-owned Diablo data + pinned DevilutionX checkout
                         |
                         v
             dxai_observation_probe.exe
                         |
       player-observable C++ projection only
                         |
               one JSON document on stdout
                         |
              Python Observation.from_dict
                         |
              contract + JSON-Schema validation
```

The probe is read-only after initialization. It may call the engine's existing initialization routines because they construct the game state; it must not write to engine arrays to manufacture an observation. It must not expose raw pointers, RNG state, item seeds, monster AI state, unexplored map contents, or hidden entities.

The user asset path is a runtime argument. The orchestration sets a separate temporary preference/configuration root so the probe does not write saves or settings into the user's Diablo installation.

## Observation contract

The existing `dxai.observation.v1` contract is extended additively with `player.inventory`.

Each inventory record contains:

- `container`: `EQUIPPED`, `INVENTORY`, or `BELT`;
- `slot`: the public slot index within that container;
- `type_id`: a stable coarse type identifier, or `UNIDENTIFIED` when the item is not identified;
- `identified`: the engine's public identification state;
- `quantity`: only a public stack quantity where the engine exposes one, otherwise `1`.

The projection deliberately excludes item name strings, random seeds, unique IDs, affixes, generated stats, durability details, and hidden item metadata. The existing `player.potions` field remains a derived count for compatibility.

Because the current v1 observation contract requires a non-empty action array, the M0.2 probe emits one explicit `WAIT` placeholder candidate. M0.2 does not expose a step endpoint and does not submit this candidate. Candidate generation and execution begin only in M0.3; the placeholder must not be treated as evidence that the action bridge is implemented.

## Engine initialization

The probe will:

1. set `HeadlessMode` before loading assets;
2. set the engine base/pref/config paths so game data is read from the supplied runtime path while mutable preferences go to a temporary root;
3. load core, game, player, spell, monster, item, object, and quest data through DevilutionX routines;
4. configure single-player Diablo mode and the supplied deterministic seed;
5. create one Warrior and enter the first standard dungeon level through the existing level-loading path;
6. project the resulting player, visible monsters, bounded tile window, and player inventory;
7. validate the serialized observation before writing it to stdout.

If the asset path is absent or required game data cannot be loaded, the probe emits a structured error on stderr and exits non-zero. It must never open a modal dialog.

## Visibility rules

- Player state is always exported for the local player.
- A monster is exported only when the engine reports its tile currently visible to the player.
- Tile terrain and walkability are exported only for explored tiles; unknown tiles use `terrain_id = -1`, `walkable = false`, and `occupied = false`.
- Occupancy is exported only for visible tiles.
- Entity IDs are derived from the episode-local active-monster index and are not stable across episodes.
- No full map, hidden monster, hidden item, future event, or engine AI field is exported.

## Failure handling

The probe uses stable error classes:

- `INVALID_ARGUMENT` for malformed or unsafe paths/seed arguments;
- `UPSTREAM_COMMIT_MISMATCH` before build or run;
- `ASSET_DATA_UNAVAILABLE` for missing/unreadable Diablo data;
- `ENGINE_INITIALIZATION_FAILED` for a failed headless game setup;
- `OBSERVATION_CONTRACT_FAILED` if the projected state violates the v1 contract.

The error text may include diagnostics, but must not include proprietary asset contents or dump raw engine state.

## Verification gates

The implementation is complete only when all of these are demonstrated:

1. Python unit tests cover inventory round-trip, visibility filtering, and structured probe errors.
2. JSON Schema examples and the C++ bridge contract accept the new inventory field.
3. The exact pinned upstream commit builds the probe in a documented configuration.
4. The supplied local Diablo data produces one schema-valid observation without opening a UI.
5. Two runs with the same seed and build produce byte-identical canonical observation JSON.
6. A run with a missing asset path fails with `ASSET_DATA_UNAVAILABLE` and does not create a modal dialog.
7. Repository scans show no MPQ, save, or machine-specific asset path tracked or copied into artifacts.

The full determinism gate over repeated trajectories, legal candidates, and state transitions remains M0.4/M0.5 work and is not claimed by this specification.
