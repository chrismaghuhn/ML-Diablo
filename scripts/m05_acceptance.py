#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import platform
import random
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dxai.contracts.serialization import canonical_json
from dxai.diagnostics.metrics import (
    FailureCounter,
    latency_summary_ns,
    process_alive,
    runtime_directory_metrics,
    sample_resources,
)
from dxai.env.client import DevilutionXEnvironment
from dxai.env.replay import (
    ReplayDivergence,
    play_engine_replay,
    record_engine_replay,
    semantic_observation_sha256,
)
from dxai.env.vector import VectorDevilutionXEnvironment, VectorEnvironmentError
from dxai.protocol.lifecycle import (
    ADAPTER_REVISION,
    BUILD_FINGERPRINT,
    DEVILUTIONX_REVISION,
    ProcessErrorCode,
    ProcessProtocolError,
)

TASK_ID = "combat.single_melee.v0"
REQUIRED_INPUT_NAMES = (
    "DXAI_M04_PROBE",
    "DXAI_DIABLO_DATA",
    "DXAI_DEVILUTIONX_CORE_ASSETS",
    "DXAI_DEVILUTIONX_RUNTIME",
)
STRUCTURED_LIMITATIONS = frozenset({ProcessErrorCode.NO_SUPPORTED_CANDIDATES.value})


@dataclass(frozen=True, slots=True)
class ExternalInputs:
    probe: Path | None
    diablo_data: Path | None
    core_assets: Path | None
    runtime: Path | None

    @classmethod
    def from_mapping(cls, values: Mapping[str, str]) -> ExternalInputs:
        return cls(
            probe=_existing_path(values.get("DXAI_M04_PROBE"), file=True),
            diablo_data=_existing_path(values.get("DXAI_DIABLO_DATA"), directory=True),
            core_assets=_existing_path(
                values.get("DXAI_DEVILUTIONX_CORE_ASSETS"), directory=True
            ),
            runtime=_existing_path(values.get("DXAI_DEVILUTIONX_RUNTIME"), directory=True),
        )

    @classmethod
    def from_environment(cls) -> ExternalInputs:
        return cls.from_mapping(os.environ)

    @property
    def missing_names(self) -> tuple[str, ...]:
        values = (self.probe, self.diablo_data, self.core_assets, self.runtime)
        return tuple(
            name
            for name, value in zip(REQUIRED_INPUT_NAMES, values, strict=True)
            if value is None
        )

    @property
    def complete(self) -> bool:
        return not self.missing_names


def seed_schedule(*, start: int, count: int) -> tuple[int, ...]:
    if start < 0 or count < 0:
        raise ValueError("seed schedule start and count must be non-negative")
    return tuple(range(start, start + count))


def build_pending_report(inputs: ExternalInputs) -> dict[str, Any]:
    return {
        "schema_version": "dxai.m05.report.v1",
        "status": "PENDING_EXTERNAL_INPUTS",
        "missing_inputs": list(inputs.missing_names),
        "warm_reset": "DEFERRED",
        "real_acceptance": "NOT_RUN",
    }


def write_run_report(
    output: Path,
    manifest: Mapping[str, Any],
    metrics: Mapping[str, Any],
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    _atomic_json_write(output / "manifest.json", manifest)
    _atomic_json_write(output / "metrics.json", metrics)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M0.5 replay/soak/throughput harness")
    parser.add_argument(
        "--mode",
        choices=("replay", "stress", "soak", "long", "throughput", "parallel", "all"),
        default="all",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--asset-fingerprint", default=os.environ.get("DXAI_ASSET_SET_FINGERPRINT"))
    parser.add_argument("--recorded-episodes", type=int, default=100)
    parser.add_argument("--playback-repetitions", type=int, default=10)
    parser.add_argument("--replay-steps", type=int, default=8)
    parser.add_argument("--legal-steps", type=int, default=10_000)
    parser.add_argument("--soak-episodes", type=int, default=1_000)
    parser.add_argument("--episode-steps", type=int, default=8)
    parser.add_argument("--long-steps", type=int, default=10_000)
    args = parser.parse_args(argv)

    inputs = ExternalInputs.from_environment()
    if not inputs.complete:
        report = build_pending_report(inputs)
        write_run_report(args.output, report, {"status": report["status"]})
        print(canonical_json(report))
        return 0
    if not args.asset_fingerprint:
        report = {
            "schema_version": "dxai.m05.report.v1",
            "status": "PENDING_ASSET_FINGERPRINT",
            "missing_inputs": ["DXAI_ASSET_SET_FINGERPRINT or --asset-fingerprint"],
            "warm_reset": "DEFERRED",
            "real_acceptance": "NOT_RUN",
        }
        write_run_report(args.output, report, {"status": report["status"]})
        print(canonical_json(report))
        return 0

    try:
        metrics = run_mode(args.mode, inputs, args.output, args)
    except Exception as error:
        report = _base_manifest(args, status="INFRASTRUCTURE_FAILURE")
        metrics = {"unexpected_error": type(error).__name__, "message": str(error)}
        write_run_report(args.output, report, metrics)
        raise
    report = _base_manifest(args, status="REAL_GATES_EXECUTED")
    write_run_report(args.output, report, metrics)
    print(canonical_json(report))
    print(canonical_json(metrics))
    return 0


def run_mode(
    mode: str,
    inputs: ExternalInputs,
    output: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    if mode == "replay":
        return run_replay_gate(
            inputs,
            output,
            asset_fingerprint=args.asset_fingerprint,
            episode_count=args.recorded_episodes,
            playback_repetitions=args.playback_repetitions,
            steps_per_episode=args.replay_steps,
        )
    if mode == "stress":
        return run_legal_stress(
            inputs,
            output,
            asset_fingerprint=args.asset_fingerprint,
            target_steps=args.legal_steps,
        )
    if mode == "soak":
        return run_cold_soak(
            inputs,
            output,
            episode_count=args.soak_episodes,
            steps_per_episode=args.episode_steps,
        )
    if mode == "long":
        return run_long_worker_soak(
            inputs,
            output,
            target_steps=args.long_steps,
        )
    if mode == "throughput":
        return run_throughput(inputs, output, steps_per_episode=args.episode_steps)
    if mode == "parallel":
        return run_parallel(
            inputs,
            output,
            asset_fingerprint=args.asset_fingerprint,
            steps_per_episode=args.episode_steps,
        )
    return run_all(inputs, output, args)


def run_all(
    inputs: ExternalInputs,
    output: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    return {
        "replay": run_replay_gate(
            inputs,
            output,
            asset_fingerprint=args.asset_fingerprint,
            episode_count=args.recorded_episodes,
            playback_repetitions=args.playback_repetitions,
            steps_per_episode=args.replay_steps,
        ),
        "stress": run_legal_stress(
            inputs,
            output,
            asset_fingerprint=args.asset_fingerprint,
            target_steps=args.legal_steps,
        ),
        "soak": run_cold_soak(
            inputs,
            output,
            episode_count=args.soak_episodes,
            steps_per_episode=args.episode_steps,
        ),
        "long": run_long_worker_soak(inputs, output, target_steps=args.long_steps),
        "throughput": run_throughput(inputs, output, steps_per_episode=args.episode_steps),
        "parallel": run_parallel(
            inputs,
            output,
            asset_fingerprint=args.asset_fingerprint,
            steps_per_episode=args.episode_steps,
        ),
    }


def run_replay_gate(
    inputs: ExternalInputs,
    output: Path,
    *,
    asset_fingerprint: str,
    episode_count: int,
    playback_repetitions: int,
    steps_per_episode: int,
) -> dict[str, Any]:
    if min(episode_count, playback_repetitions, steps_per_episode) <= 0:
        raise ValueError("replay counts and steps must be positive")
    replay_root = output / "replays"
    replay_root.mkdir(parents=True, exist_ok=True)
    failures = FailureCounter()
    recorded: list[Path] = []
    for seed in seed_schedule(start=0, count=episode_count):
        destination = replay_root / f"seed-{seed}"
        environment = _new_environment(inputs, output / "record-workers" / f"seed-{seed}")
        try:
            record_engine_replay(
                environment,
                destination,
                seed=seed,
                task_id=TASK_ID,
                asset_set_fingerprint=asset_fingerprint,
                select_candidate=lambda observation: observation.legal_actions[0].candidate_id,
                max_steps=steps_per_episode,
            )
            recorded.append(destination)
        except (ProcessProtocolError, ReplayDivergence) as error:
            failures.record(error)
        finally:
            environment.close()

    playback_successes = 0
    divergences = 0
    for replay_path in recorded:
        for repetition in range(playback_repetitions):
            environment = _new_environment(
                inputs,
                output / "playback-workers" / replay_path.name / str(repetition),
            )
            try:
                play_engine_replay(
                    environment,
                    replay_path,
                    asset_set_fingerprint=asset_fingerprint,
                )
                playback_successes += 1
            except ReplayDivergence as error:
                divergences += 1
                failures.record(error.code)
            except ProcessProtocolError as error:
                failures.record(error)
            finally:
                environment.close()
    return {
        "episodes_requested": episode_count,
        "episodes_recorded": len(recorded),
        "playback_requested": len(recorded) * playback_repetitions,
        "playback_successes": playback_successes,
        "replay_divergences": divergences,
        "failure_counts": failures.to_dict(),
    }


def run_legal_stress(
    inputs: ExternalInputs,
    output: Path,
    *,
    asset_fingerprint: str,
    target_steps: int,
) -> dict[str, Any]:
    del asset_fingerprint
    if target_steps <= 0:
        raise ValueError("target_steps must be positive")
    failures = FailureCounter()
    random_source = random.Random(0xA05)
    environment = _new_environment(inputs, output / "stress-workers")
    valid_steps = 0
    attempts = 0
    episodes = 0
    observation = None
    try:
        while valid_steps < target_steps:
            if observation is None:
                try:
                    observation = environment.reset(seed=episodes, task_id=TASK_ID)
                    episodes += 1
                except (ProcessProtocolError, ReplayDivergence) as error:
                    failures.record(error)
                    if _is_fatal_failure(error):
                        break
                    episodes += 1
                    continue
            attempts += 1
            candidate_id = random_source.choice(observation.legal_actions).candidate_id
            try:
                observation = environment.step(candidate_id).observation
                valid_steps += 1
            except (ProcessProtocolError, ReplayDivergence) as error:
                failures.record(error)
                observation = None
                if _is_fatal_failure(error):
                    break
    finally:
        environment.close()
    return {
        "target_steps": target_steps,
        "valid_steps": valid_steps,
        "attempts": attempts,
        "episodes_needed": episodes,
        "failure_counts": failures.to_dict(),
    }


def run_cold_soak(
    inputs: ExternalInputs,
    output: Path,
    *,
    episode_count: int,
    steps_per_episode: int,
) -> dict[str, Any]:
    if min(episode_count, steps_per_episode) <= 0:
        raise ValueError("soak counts and steps must be positive")
    failures = FailureCounter()
    manager_samples: list[dict[str, Any]] = []
    worker_samples: list[dict[str, Any]] = []
    worker_pids: set[int] = set()
    completed = 0
    steps = 0
    runtime_root = output / "soak-workers"
    environment = _new_environment(inputs, runtime_root)
    try:
        manager_samples.append(sample_resources(os.getpid(), runtime_root).to_dict())
        for seed in seed_schedule(start=0, count=episode_count):
            try:
                observation = environment.reset(seed=seed, task_id=TASK_ID)
                if environment.worker_pid is not None:
                    worker_pids.add(environment.worker_pid)
                for _ in range(steps_per_episode):
                    response = environment.step(observation.legal_actions[0].candidate_id)
                    observation = response.observation
                    steps += 1
                completed += 1
            except (ProcessProtocolError, ReplayDivergence) as error:
                failures.record(error)
                if _is_fatal_failure(error):
                    break
            manager_samples.append(sample_resources(os.getpid(), runtime_root).to_dict())
            if environment.worker_pid is not None:
                worker_pids.add(environment.worker_pid)
                worker_samples.append(
                    sample_resources(environment.worker_pid, runtime_root).to_dict()
                )
    finally:
        environment.close()
    manager_samples.append(sample_resources(os.getpid(), runtime_root).to_dict())
    alive_after_close = [process_alive(pid) for pid in sorted(worker_pids)]
    orphan_workers: int | str
    if any(state == "UNAVAILABLE" for state in alive_after_close):
        orphan_workers = "UNAVAILABLE"
    else:
        orphan_workers = sum(state is True for state in alive_after_close)
    return {
        "episodes_attempted": episode_count,
        "episodes_completed": completed,
        "steps_completed": steps,
        "failure_counts": failures.to_dict(),
        "manager_resource_samples": manager_samples,
        "worker_resource_samples": worker_samples,
        "orphan_workers": orphan_workers,
        "temporary_runtime_remnants": runtime_directory_metrics(runtime_root),
    }


def run_long_worker_soak(
    inputs: ExternalInputs,
    output: Path,
    *,
    target_steps: int,
) -> dict[str, Any]:
    if target_steps <= 0:
        raise ValueError("target_steps must be positive")
    failures = FailureCounter()
    environment = _new_environment(inputs, output / "long-worker")
    valid_steps = 0
    segments = 0
    try:
        observation = environment.reset(seed=0, task_id=TASK_ID)
        segments = 1
        while valid_steps < target_steps:
            try:
                observation = environment.step(
                    observation.legal_actions[0].candidate_id
                ).observation
                valid_steps += 1
            except (ProcessProtocolError, ReplayDivergence) as error:
                failures.record(error)
                if _is_fatal_failure(error):
                    break
                observation = environment.reset(seed=segments, task_id=TASK_ID)
                segments += 1
    finally:
        environment.close()
    return {
        "target_steps": target_steps,
        "steps_completed": valid_steps,
        "segments": segments,
        "failure_counts": failures.to_dict(),
        "segmentation_reason": (
            "NO_SUPPORTED_CANDIDATES limits are reported, not replaced with WAIT"
        ),
    }


def run_throughput(
    inputs: ExternalInputs,
    output: Path,
    *,
    steps_per_episode: int,
) -> dict[str, Any]:
    if steps_per_episode <= 0:
        raise ValueError("steps_per_episode must be positive")
    startup_samples: list[int] = []
    health_samples: list[int] = []
    reset_samples: list[int] = []
    step_samples: list[int] = []
    step_count = 0
    failures = FailureCounter()
    environment = _new_environment(inputs, output / "throughput-workers")
    try:
        for seed in range(3):
            start = time.perf_counter_ns()
            observation = environment.reset(seed=seed, task_id=TASK_ID)
            reset_samples.append(time.perf_counter_ns() - start)
            if environment.last_worker_startup_ns is not None:
                startup_samples.append(environment.last_worker_startup_ns)
            start = time.perf_counter_ns()
            environment.health_check()
            health_samples.append(time.perf_counter_ns() - start)
            for _ in range(steps_per_episode):
                start = time.perf_counter_ns()
                response = environment.step(observation.legal_actions[0].candidate_id)
                step_samples.append(time.perf_counter_ns() - start)
                observation = response.observation
                step_count += 1
    except (ProcessProtocolError, ReplayDivergence) as error:
        failures.record(error)
    finally:
        environment.close()
    return {
        "warmup_samples_excluded": 0,
        "warmup_policy": (
            "No warm-up samples are excluded: every sample is an explicitly timed cold reset, "
            "Health check, or Step."
        ),
        "reset_latency": latency_summary_ns(reset_samples, warmup_count=0)
        if reset_samples
        else "UNAVAILABLE",
        "worker_startup_latency": latency_summary_ns(startup_samples, warmup_count=0)
        if startup_samples
        else "UNAVAILABLE",
        "health_latency": latency_summary_ns(health_samples, warmup_count=0)
        if health_samples
        else "UNAVAILABLE",
        "step_latency": latency_summary_ns(step_samples, warmup_count=0)
        if step_samples
        else "UNAVAILABLE",
        "steps_per_second": _rate(step_count, sum(step_samples)),
        "episodes_per_second": _rate(len(reset_samples), sum(reset_samples)),
        "worker_startups_per_second": _rate(len(startup_samples), sum(startup_samples)),
        "health_checks_per_second": _rate(len(health_samples), sum(health_samples)),
        "failure_counts": failures.to_dict(),
    }


def run_parallel(
    inputs: ExternalInputs,
    output: Path,
    *,
    asset_fingerprint: str,
    steps_per_episode: int,
) -> dict[str, Any]:
    del asset_fingerprint
    if steps_per_episode <= 0:
        raise ValueError("steps_per_episode must be positive")
    results: dict[str, Any] = {}
    for worker_count in (1, 2, 4):
        failures = FailureCounter()
        vector: VectorDevilutionXEnvironment | None = None
        try:
            assert inputs.probe is not None
            assert inputs.diablo_data is not None
            assert inputs.core_assets is not None
            vector = VectorDevilutionXEnvironment(
                worker_count,
                executable=inputs.probe,
                assets_path=inputs.diablo_data,
                core_assets_path=inputs.core_assets,
                engine_runtime_path=inputs.runtime,
                runtime_root=output / "parallel-workers" / str(worker_count),
            )
            reset_started = time.perf_counter_ns()
            observations = vector.reset_many([123] * worker_count, TASK_ID)
            reset_elapsed = time.perf_counter_ns() - reset_started
            health_samples: list[int] = []
            startup_samples = [
                environment.last_worker_startup_ns
                for environment in vector.environments
                if environment.last_worker_startup_ns is not None
            ]
            for environment in vector.environments:
                health_started = time.perf_counter_ns()
                environment.health_check()
                health_samples.append(time.perf_counter_ns() - health_started)
            same_seed_initial_hashes = [semantic_observation_sha256(item) for item in observations]
            batch_step_samples: list[int] = []
            steps_completed = 0
            for _ in range(steps_per_episode):
                step_started = time.perf_counter_ns()
                responses = vector.step_many(
                    [observation.legal_actions[0].candidate_id for observation in observations]
                )
                batch_step_samples.append(time.perf_counter_ns() - step_started)
                observations = tuple(response.observation for response in responses)
                steps_completed += len(responses)
            results[str(worker_count)] = {
                "distinct_worker_pids": (
                    all(pid is not None for pid in vector.worker_pids)
                    and len(set(vector.worker_pids)) == worker_count
                ),
                "distinct_runtime_roots": (
                    all(root is not None for root in vector.runtime_roots)
                    and len(set(vector.runtime_roots)) == worker_count
                ),
                "same_seed_initial_trace_equal": len(set(same_seed_initial_hashes)) == 1,
                "steps_completed": steps_completed,
                "reset_latency": latency_summary_ns([reset_elapsed], warmup_count=0),
                "health_latency": latency_summary_ns(health_samples, warmup_count=0),
                "step_batch_latency": latency_summary_ns(batch_step_samples, warmup_count=0),
                "worker_startup_latency": (
                    latency_summary_ns(startup_samples, warmup_count=0)
                    if startup_samples
                    else "UNAVAILABLE"
                ),
                "steps_per_second": _rate(steps_completed, sum(batch_step_samples)),
                "failure_counts": failures.to_dict(),
            }
        except (ProcessProtocolError, ReplayDivergence, VectorEnvironmentError) as error:
            if not _is_known_structured_failure(error):
                raise
            failures.record(error)
            results[str(worker_count)] = {
                "steps_completed": 0,
                "failure_counts": failures.to_dict(),
            }
        finally:
            if vector is not None:
                vector.close()
    return results


def _new_environment(inputs: ExternalInputs, runtime_root: Path) -> DevilutionXEnvironment:
    assert inputs.probe is not None
    assert inputs.diablo_data is not None
    assert inputs.core_assets is not None
    assert inputs.runtime is not None
    return DevilutionXEnvironment(
        executable=inputs.probe,
        assets_path=inputs.diablo_data,
        core_assets_path=inputs.core_assets,
        engine_runtime_path=inputs.runtime,
        runtime_root=runtime_root,
        timeout_seconds=60.0,
    )


def _existing_path(
    value: str | None, *, file: bool = False, directory: bool = False
) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if file and path.is_file():
        return path
    if directory and path.is_dir():
        return path
    return None


def _atomic_json_write(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical_json(value) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _base_manifest(args: argparse.Namespace, *, status: str) -> dict[str, Any]:
    return {
        "schema_version": "dxai.m05.report.v1",
        "status": status,
        "platform": platform.system(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "devilutionx_revision": DEVILUTIONX_REVISION,
        "adapter_revision": ADAPTER_REVISION,
        "build_fingerprint": BUILD_FINGERPRINT,
        "worker_counts": [1, 2, 4],
        "configuration": {
            "mode": args.mode,
            "recorded_episodes": args.recorded_episodes,
            "playback_repetitions": args.playback_repetitions,
            "replay_steps": args.replay_steps,
            "legal_steps": args.legal_steps,
            "soak_episodes": args.soak_episodes,
            "episode_steps": args.episode_steps,
            "long_steps": args.long_steps,
        },
        "created_at_utc": datetime.now(UTC).isoformat(),
    }


def _is_fatal_failure(error: BaseException) -> bool:
    if isinstance(error, ProcessProtocolError):
        return error.code.value not in STRUCTURED_LIMITATIONS
    return False


def _is_known_structured_failure(error: BaseException) -> bool:
    if isinstance(error, (ProcessProtocolError, ReplayDivergence)):
        return True
    if isinstance(error, VectorEnvironmentError):
        return _is_known_structured_failure(error.cause)
    return False


def _rate(count: int, elapsed_ns: int) -> float | str:
    if elapsed_ns <= 0:
        return "UNAVAILABLE"
    return count * 1_000_000_000 / elapsed_ns


if __name__ == "__main__":
    raise SystemExit(main())
