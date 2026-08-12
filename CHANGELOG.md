# Changelog

## M0.4 - 2026-08-12

- Added a persistent `--env-stdio` native worker around the M0.3 semantic
  DevilutionX slice.
- Added strict `dxai.process.v1` UTF-8 JSON-Lines with a 1 MiB limit,
  Health/Reset/Step/Error responses and explicit lifecycle states.
- Added process-unique episode IDs, step/candidate-set identity validation,
  bounded 128-entry request idempotency and Python cold-reset replacement.
- Added stdout protocol isolation, stderr diagnostics, canonical lifecycle
  trace hashing, native/Python contract tests and an opt-in 32-step real gate.
- Validated the real asset-dependent gate against the pinned DevilutionX
  release and user-owned local data: Health/Reset, 32 same-worker Steps,
  exactly-once duplicate replay, rejection non-mutation, cold-reset isolation,
  same-seed trace equality and worker cleanup all passed.
- Kept rewards, terminal flags, warm reset, broader actions, replay and ML out
  of scope; global M0 acceptance remains separate.

## M0.3 - 2026-08-12

- Added the first real semantic DevilutionX step for the controlled fixture.
- Added native, observability-audited adjacent `MOVE_TO_TILE` candidates with
  deterministic semantic ordering, deduplication and dense IDs.
- Added candidate-set canonical identity and SHA-256 binding before native
  `MakePlrPath` execution.
- Added bounded advancement to the next controllable boundary and the minimal
  `dxai.probe.step.v1` envelope with fresh next candidates.
- Added structured stale, state-mismatch, no-supported-candidates and action-
  resolution failures plus Python/native contract coverage.
- Kept persistent IPC, reset service, broader action families, rewards and ML
  out of scope.

## M0.2 - 2026-08-12

- Added a separate, pinned-commit DevilutionX read-only observation probe.
- Added real player, visible-entity, bounded-tile and sanitized-inventory
  mapping for `dxai.observation.v1`.
- Added separate original-data, core-asset and engine-runtime path handling.
- Added structured native probe errors, Python client integration and runtime
  library preflight checks.
- Added deterministic, schema, missing-asset and full local verification gates.
- Kept candidate execution, `step`, IPC and RL explicitly out of scope.

## 0.1.0 - 2026-08-11

- Initial architecture and ML research scaffold.
- Runnable deterministic mock environment and baseline agents.
- Versioned observation/action/trajectory contracts.
- Atomic JSONL trajectory writer with manifests, checksums and abort cleanup.
- Strict JSON, semantic action payload and finite-value validation.
- Candidate-action recurrent Q-network scaffold.
- Prioritized sequence replay and dual demonstration/agent sampler.
- Standalone C++ bridge contract and tests.
- Detailed integration, curriculum, evaluation, legal and milestone documentation.
