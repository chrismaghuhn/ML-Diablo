# Changelog

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
