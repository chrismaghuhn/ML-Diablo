from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from dxai.env.client import DevilutionXEnvironment
from dxai.env.determinism import canonical_trace_sha256
from dxai.protocol.lifecycle import (
    ProcessErrorCode,
    make_step_request,
    parse_process_response,
)

TASK_ID = "combat.single_melee.v0"


def _required_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"set {name} to run the local DevilutionX M0.4 integration test")
    path = Path(value)
    if not path.exists():
        pytest.skip(f"{name} does not point to an existing external input: {path}")
    return path


def _environment(tmp_path: Path) -> DevilutionXEnvironment:
    return DevilutionXEnvironment(
        executable=_required_path("DXAI_M04_PROBE"),
        assets_path=_required_path("DXAI_DIABLO_DATA"),
        core_assets_path=_required_path("DXAI_DEVILUTIONX_CORE_ASSETS"),
        engine_runtime_path=_required_path("DXAI_DEVILUTIONX_RUNTIME"),
        runtime_root=tmp_path / "workers",
        timeout_seconds=60.0,
    )


def _trace_for_32_steps(tmp_path: Path, seed: int = 123) -> tuple[str, int, list[dict[str, Any]]]:
    env = _environment(tmp_path)
    trace: list[dict[str, Any]] = []
    try:
        observation = env.reset(seed=seed, task_id=TASK_ID)
        pid = env.worker_pid
        assert pid is not None
        trace.append(
            {
                "pid": pid,
                "runtime_root": str(tmp_path / "workers"),
                "episode_id": observation.episode_id,
                "observation": observation.to_dict(),
                "candidate_set_sha256": env.candidate_set_sha256,
            }
        )
        for expected_step_id in range(32):
            assert env.observation is not None
            action = env.observation.legal_actions[0]
            response = env.step(action.candidate_id)
            assert response.previous_step_id == expected_step_id
            assert response.observation.step_id == expected_step_id + 1
            assert env.worker_pid == pid
            trace.append(
                {
                    "request_id": response.request_id,
                    "pid": pid,
                    "episode_id": response.episode_id,
                    "engine_tick": response.observation.engine_tick,
                    "action": response.applied_action.to_dict(),
                    "observation": response.observation.to_dict(),
                    "candidate_set_sha256": response.candidate_set_sha256,
                }
            )
        return canonical_trace_sha256(trace), pid, trace
    finally:
        env.close()


def test_real_m04_32_steps_keep_one_pid_and_same_seed_trace_is_equal(
    tmp_path: Path,
) -> None:
    first_hash, first_pid, first_trace = _trace_for_32_steps(tmp_path / "run-a")
    second_hash, second_pid, second_trace = _trace_for_32_steps(tmp_path / "run-b")

    assert len(first_trace) == 33
    assert len(second_trace) == 33
    assert first_pid > 0
    assert second_pid > 0
    assert first_hash == second_hash


def test_real_m04_rejected_step_does_not_mutate_and_duplicate_replays_once(
    tmp_path: Path,
) -> None:
    env = _environment(tmp_path)
    try:
        observation = env.reset(seed=123, task_id=TASK_ID)
        worker = env._worker
        assert worker is not None
        action = observation.legal_actions[0]
        candidate_hash = env.candidate_set_sha256
        assert candidate_hash is not None

        stale = make_step_request(
            3,
            episode_id=observation.episode_id,
            expected_step_id=1,
            candidate_id=action.candidate_id,
            candidate_set_sha256=candidate_hash,
        )
        stale_response = parse_process_response(worker.request(stale))
        assert getattr(stale_response, "error_code", None) is ProcessErrorCode.STALE_STEP

        valid = make_step_request(
            4,
            episode_id=observation.episode_id,
            expected_step_id=0,
            candidate_id=action.candidate_id,
            candidate_set_sha256=candidate_hash,
        )
        first_response = worker.request(valid)
        duplicate_response = worker.request(valid)
        assert duplicate_response == first_response
        parsed = parse_process_response(first_response)
        assert parsed.observation.step_id == 1
    finally:
        env.close()


def test_real_m04_cold_reset_isolates_a_b_a(tmp_path: Path) -> None:
    env = _environment(tmp_path)
    try:
        first = env.reset(seed=123, task_id=TASK_ID)
        first_semantics = canonical_trace_sha256(
            {"episode_id": first.episode_id, "observation": first.to_dict()}
        )
        first_pid = env.worker_pid
        second = env.reset(seed=456, task_id=TASK_ID)
        second_pid = env.worker_pid
        third = env.reset(seed=123, task_id=TASK_ID)
        third_semantics = canonical_trace_sha256(
            {"episode_id": third.episode_id, "observation": third.to_dict()}
        )

        assert first_semantics == third_semantics
        assert first.episode_id != second.episode_id != third.episode_id
        assert first_pid is not None
        assert second_pid is not None
        assert env.worker_pid is not None
    finally:
        env.close()
