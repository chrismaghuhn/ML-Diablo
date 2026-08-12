# M0.4 Persistent Environment Lifecycle Design

**Baseline:** `b7957c9e398b42559ab2a36a88df981c8013b5d3`
**Pinned DevilutionX:** `07385842840437cc9a785b195f5b40b121eaeb1c`
**Scope:** persistent multi-step lifecycle only; no learning, rewards, terminal gameplay, warm reset, or new action kind.

## Decision

M0.4 adds a single native `--env-stdio` mode to the existing observation probe. A
worker owns exactly one DevilutionX episode. It initializes the existing M0.3
fixture only when it receives its first Reset request, then retains the native
globals and loaded level while it serves any number of Steps. Python implements
cold reset by closing the current worker and starting a fresh worker with a fresh
trusted runtime root.

The process transport is one UTF-8 JSON object per line. The process envelope is
versioned as `dxai.process.v1`; the observation and action contracts remain
`dxai.observation.v1` and `dxai.action.v1`. The old Protobuf is not redefined:
its reward and terminal fields remain outside the M0.4 authoritative surface.

## Native worker

The current M0.3 functions are reused directly:

```text
InitializeEngine(request seed)
GenerateMoveCandidates()
CanonicalCandidateSetKey()
MakePlrPath()
AdvancePinnedGameLogicBody()
SerializeObservation()
```

The worker state is:

```text
READY
  active episode = none
EPISODE_ACTIVE
  episode_id
  seed/task
  step_id
  cumulative engine_tick
  current candidates + candidate_set_sha256
  bounded request cache
FAULTED
  no further Steps
```

Reset is accepted only once by a worker. The first successful Reset creates a
fresh lifecycle episode ID composed from a process-unique nonce and a local
counter; it is not derived only from the seed. Step ID starts at zero and is
incremented exactly once only after native action resolution reaches the next
controllable boundary and the next observation/candidate set is built.

Before mutation, a Step validates the process version, state, episode ID,
expected step ID, candidate-set digest, and candidate ID. The existing M0.3
candidate generation and canonical identity are the only legality authority.

The request cache holds the last 128 completed request IDs. Each entry includes
the canonical request fingerprint and the complete serialized response. Exact
duplicates replay the response. A reused ID with a different fingerprint is a
protocol error. IDs below the monotonic high-water mark are rejected once their
cache entry has been evicted, preventing an old request from becoming a new
mutation.

## Wire contract

The maximum body size is 1 MiB, measured in UTF-8 bytes before parsing. Requests
are closed objects with these message types:

```text
health_request  {type, protocol_version, request_id}
reset_request   {type, protocol_version, request_id, seed, task_id}
step_request    {type, protocol_version, request_id, episode_id,
                 expected_step_id, candidate_id, candidate_set_sha256}
```

Every accepted line produces one response line. The response types are
`health_response`, `reset_response`, `step_response`, and `error_response`.
Malformed UTF-8, malformed JSON, unknown fields, missing fields, unsupported
versions, invalid numeric types, and oversized lines are rejected before engine
mutation. Fatal framing/native invariant failures transition the worker to
`FAULTED`.

Health exposes the process version/state, adapter revision, pinned DevilutionX
revision, build fingerprint, observation/action versions, supported task
versions/features, and PID. It never exposes local asset paths or proprietary
data contents.

The successful Reset and Step responses contain lifecycle/audit metadata,
observation, candidate-set digests, and the applied semantic action. They do not
contain reward, `terminated`, or `truncated` fields.

## Python lifecycle manager

`DevilutionXEnvironment` owns one worker handle and one current lifecycle state.
`reset(seed, task_id)` closes any existing worker, launches a new worker, waits
for and validates Health, sends Reset, and returns the validated observation.
`step(candidate_id)` sends only the candidate ID plus the current lifecycle
identity and digest, validates the response, updates local state, and returns a
rich M0.4 step response rather than manufacturing a learning transition.

The process manager has no Python legality generation. It uses the candidate IDs
already present in the current observation. `close()` closes stdin, waits for a
bounded interval, force-terminates only when necessary, and reaps the process;
repeated calls are harmless. EOF, unexpected exit, timeout, malformed response,
version mismatch, and engine fault all make the current worker unusable. The
client never retries a timed-out Step and requires Reset for recovery.

## Determinism

Canonical M0.4 traces include the observation, ordered candidates, semantic
action, engine tick, and step sequence. They replace lifecycle `episode_id` with
`<lifecycle-episode>` and exclude request IDs, PID, runtime roots, timestamps,
and process launch metadata. Seed, player/world state, candidate semantics,
engine ticks, and step ordering are never normalized. The same-seed trace hash
therefore compares game semantics while permitting the required unique episode
identity.

## Validation strategy

Pure Python tests cover strict message parsing, framing, closed fields, request
cache/idempotency, lifecycle state transitions, response validation, timeout,
EOF/crash handling, cleanup, and canonical trace hashing. Native contract tests
cover UTF-8/line framing, request parsing, request-cache eviction, state-machine
gates, and fault-state rejection. The opt-in real test reuses the pinned M0.3
fixture, performs at least 32 successful Steps in one PID, checks rejected-step
non-mutation, duplicate exactly-once behavior, A→B→A cold-reset isolation,
same-seed trace equality, and cross-reset stale identity rejection.

No proprietary assets are added to the repository. No commit, push, or pull
request is part of this task.
