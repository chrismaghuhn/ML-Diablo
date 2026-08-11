# Changelog

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
