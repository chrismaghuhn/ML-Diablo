# M0.5 Replay, Soak, Throughput and Process Isolation

This runbook covers the opt-in real-input gates for the M0.5
environment-reproducibility slice. It does not change the M0.4
`dxai.process.v1` protocol and does not publish proprietary engine inputs.

## Scope

M0.5 provides:

- closed `dxai.engine_replay.v1` artifacts;
- semantic-action playback against the current complete candidate set;
- first-divergence `REPLAY_DIVERGENCE` diagnostics;
- cold-reset, legal-step stress, long-worker and throughput modes;
- one existing native M0.4 worker per vector slot;
- observational latency, resource and structured-failure metrics.

M0.5 does not provide training trajectories, rewards, terminal/truncation
semantics, behavior-policy metadata, engine events or warm reset. Warm reset is
deferred until a complete native teardown/reinitialize path is proven.

## External inputs

The following user-owned inputs are required for real execution. Keep them
outside the repository and do not add them to Git:

```text
DXAI_M04_PROBE                 path to the built --env-stdio probe
DXAI_DIABLO_DATA               directory containing the Diablo data
DXAI_DEVILUTIONX_CORE_ASSETS   directory containing DevilutionX core assets
DXAI_DEVILUTIONX_RUNTIME       directory containing the runtime DLL
DXAI_ASSET_SET_FINGERPRINT     opaque non-path identity for the asset set
```

The harness checks that the first path is a file and the other input paths are
directories. The fingerprint is stored as an identity only; paths are never
written into replay identity or the report.

## Run

Choose an output directory outside the repository. The default counts are the
M0.5 acceptance counts:

```powershell
python scripts/m05_acceptance.py --mode all --output C:\path\outside\m05-run
```

Individual modes are available for bounded diagnostics:

```powershell
python scripts/m05_acceptance.py --mode replay --output C:\path\outside\m05-replay
python scripts/m05_acceptance.py --mode stress --output C:\path\outside\m05-stress
python scripts/m05_acceptance.py --mode soak --output C:\path\outside\m05-soak
python scripts/m05_acceptance.py --mode long --output C:\path\outside\m05-long
python scripts/m05_acceptance.py --mode throughput --output C:\path\outside\m05-throughput
python scripts/m05_acceptance.py --mode parallel --output C:\path\outside\m05-parallel
```

The replay mode records 100 episodes and plays each valid artifact 10 times.
Stress targets 10,000 valid Steps, soak targets 1,000 cold-reset episodes,
long targets 10,000 Steps on a persistent worker, and parallel mode exercises
1, 2 and 4 independent worker slots. Counts can be lowered for a smoke run by
passing the corresponding command-line options, but a smoke run is not an
acceptance result.

## Output and validity

The selected output root contains:

```text
manifest.json
metrics.json
replays/<seed>/manifest.json
replays/<seed>/steps.jsonl
```

Replay publication is atomic and manifest-last. The loader rejects partial,
corrupt, incompatible, non-finite, duplicate-key, unsafe-path and
non-contiguous artifacts. Playback stops at the first precondition,
semantic-action, post-observation, candidate-set or engine-tick divergence.

Reports count structured failures such as `PROCESS_TIMEOUT`,
`PROCESS_EXITED`, `ENGINE_FAULTED`, `NO_SUPPORTED_CANDIDATES`,
`REPLAY_DIVERGENCE`, `INVALID_CANDIDATE`, `STALE_STEP`, `STALE_EPISODE` and
`REQUEST_ID_REUSE`. Unsupported platform metrics are written as
`UNAVAILABLE`; no correctness result is inferred from a missing metric.
Throughput reports `warmup_samples_excluded=0` intentionally: the measured
samples are cold resets, Health checks and Steps, not a warmed-up steady-state
benchmark.

## Missing-input result

If any required external input is absent, the command exits successfully only
to publish a machine-readable pending report:

```json
{
  "status": "PENDING_EXTERNAL_INPUTS",
  "real_acceptance": "NOT_RUN",
  "warm_reset": "DEFERRED"
}
```

The report lists only missing variable names. It is not a real-gate PASS.
M0.5 remains `implementation complete, real acceptance pending` until the
100-recording/1,000-playback, 10,000-Step, 1,000-episode and parallel-real-
worker gates have run with the external inputs.

## Repository-only verification

Without the external inputs, run the repository-only checks from the plan and
record the pending report separately. In particular, do not substitute mock
or synthetic runs for the real acceptance counts, and do not benchmark a
manually cleared warm reset.
