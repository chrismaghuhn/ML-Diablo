# ADR 0013 - M0.2 uses an external read-only observation probe

- Status: Accepted
- Date: 2026-08-12

## Decision

The first real DevilutionX integration is implemented as a separate C++
observation probe linked against a user-owned build of the pinned upstream
checkout. The repository contains only the probe source, its contract-facing
build definition and the Python launcher/client; it does not vendor or patch
DevilutionX.

The probe accepts separate paths for original Diablo data, loose DevilutionX
core assets and the engine runtime. It initializes one deterministic
single-player task and emits one `dxai.observation.v1` JSON object to stdout.
Errors are structured JSON on stderr.

The probe is read-only at the agent boundary. It has no candidate execution,
decision-boundary stepping, IPC server or reinforcement-learning loop.

## Rationale

This keeps build, asset loading, observation mapping and future action
execution independently diagnosable. It also prevents Python from becoming a
second rules engine and preserves the repository's asset/licensing boundary.
The split asset paths are required because the original MPQ and the loose
DevilutionX core assets serve different loader responsibilities.

## Consequences

- M0.2 can validate a real player-observable payload before action semantics
  are introduced.
- The native probe remains tied to the pinned upstream ABI and must be rebuilt
  after an upstream change.
- M0.3 must add engine-generated legal candidates and candidate-ID-only
  execution without widening the Python boundary.
- Full M0 acceptance remains open until reset, step, legality, replay, IPC and
  observability gates pass.
