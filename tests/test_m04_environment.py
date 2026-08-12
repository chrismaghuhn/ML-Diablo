from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, ClassVar

import pytest

from dxai.contracts.observations import Observation
from dxai.env.client import DevilutionXEnvironment, _WorkerProcess
from dxai.env.legal import candidate_set_sha256
from dxai.protocol.lifecycle import (
    ACTION_VERSION,
    ADAPTER_REVISION,
    BUILD_FINGERPRINT,
    DEVILUTIONX_REVISION,
    OBSERVATION_VERSION,
    PROCESS_PROTOCOL_VERSION,
    SUPPORTED_FEATURES,
    SUPPORTED_TASK_VERSIONS,
    ProcessErrorCode,
    ProcessProtocolError,
    make_health_request,
    parse_process_response,
)

TASK_ID = "combat.single_melee.v0"


def _observations() -> tuple[Observation, Observation]:
    payload = json.loads(
        (Path(__file__).parents[1] / "schemas/examples/probe_step.example.json").read_text(
            encoding="utf-8"
        )
    )
    first = Observation.from_dict(payload["observation"])
    second = Observation.from_dict(payload["next_observation"])
    return first, second


def _health(request_id: int, pid: int, state: str = "READY") -> dict[str, Any]:
    return {
        "type": "health_response",
        "protocol_version": PROCESS_PROTOCOL_VERSION,
        "request_id": request_id,
        "process_state": state,
        "adapter_revision": ADAPTER_REVISION,
        "devilutionx_revision": DEVILUTIONX_REVISION,
        "build_fingerprint": BUILD_FINGERPRINT,
        "observation_version": OBSERVATION_VERSION,
        "action_version": ACTION_VERSION,
        "supported_task_versions": list(SUPPORTED_TASK_VERSIONS),
        "supported_features": list(SUPPORTED_FEATURES),
        "pid": pid,
    }


class FakeWorker:
    instances: ClassVar[list[FakeWorker]] = []
    fail_with: ProcessProtocolError | None = None

    def __init__(self, *args: Any, pid: int) -> None:
        self.pid = pid
        self.closed = False
        self.seed: int | None = None
        self.requests: list[dict[str, Any]] = []
        self.instances.append(self)

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(payload)
        if self.fail_with is not None:
            raise self.fail_with
        request_id = int(payload["request_id"])
        if payload["type"] == "health_request":
            return _health(request_id, self.pid)
        if payload["type"] == "reset_request":
            first, _ = _observations()
            episode_id = f"native-episode-{self.pid}"
            self.seed = int(payload["seed"])
            first = replace(first, episode_id=episode_id, seed=self.seed)
            return {
                "type": "reset_response",
                "protocol_version": PROCESS_PROTOCOL_VERSION,
                "request_id": request_id,
                "process_state": "EPISODE_ACTIVE",
                "episode_id": episode_id,
                "observation": first.to_dict(),
                "candidate_set_sha256": candidate_set_sha256(first.legal_actions),
            }
        first, second = _observations()
        episode_id = str(payload["episode_id"])
        seed = 123 if self.seed is None else self.seed
        first = replace(first, episode_id=episode_id, seed=seed)
        second = replace(
            second,
            episode_id=episode_id,
            seed=seed,
            step_id=int(payload["expected_step_id"]) + 1,
        )
        action = first.action_by_id(int(payload["candidate_id"]))
        return {
            "type": "step_response",
            "protocol_version": PROCESS_PROTOCOL_VERSION,
            "request_id": request_id,
            "process_state": "EPISODE_ACTIVE",
            "episode_id": episode_id,
            "previous_step_id": int(payload["expected_step_id"]),
            "applied_action": action.to_dict(),
            "previous_candidate_set_sha256": payload["candidate_set_sha256"],
            "observation": second.to_dict(),
            "candidate_set_sha256": candidate_set_sha256(second.legal_actions),
        }

    def close(self) -> None:
        self.closed = True


def _environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DevilutionXEnvironment:
    executable = tmp_path / "probe.exe"
    executable.touch()
    assets = tmp_path / "assets"
    assets.mkdir()
    core_assets = tmp_path / "core-assets"
    core_assets.mkdir()
    FakeWorker.instances = []
    next_pid = iter((1001, 1002, 1003))

    def factory(*args: Any, **kwargs: Any) -> FakeWorker:
        return FakeWorker(*args, pid=next(next_pid), **kwargs)

    monkeypatch.setattr("dxai.env.client._WorkerProcess", factory)
    return DevilutionXEnvironment(
        executable=executable,
        assets_path=assets,
        core_assets_path=core_assets,
        timeout_seconds=0.1,
    )


def test_reset_replaces_worker_and_step_sends_only_lifecycle_identity_and_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _environment(tmp_path, monkeypatch)
    first = env.reset(seed=123, task_id=TASK_ID)
    assert first.step_id == 0
    selected = first.legal_actions[0]

    result = env.step(selected.candidate_id)
    assert result.observation.step_id == 1
    assert len(FakeWorker.instances) == 1
    step_request = FakeWorker.instances[0].requests[-1]
    assert set(step_request) == {
        "type",
        "protocol_version",
        "request_id",
        "episode_id",
        "expected_step_id",
        "candidate_id",
        "candidate_set_sha256",
    }
    assert "target_tile" not in step_request

    second = env.reset(seed=456, task_id=TASK_ID)
    assert second.step_id == 0
    assert FakeWorker.instances[0].closed is True
    assert len(FakeWorker.instances) == 2
    assert first.episode_id != second.episode_id
    env.close()
    env.close()


def test_timeout_marks_worker_unusable_and_requires_reset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _environment(tmp_path, monkeypatch)
    env.reset(seed=123, task_id=TASK_ID)
    FakeWorker.fail_with = ProcessProtocolError(ProcessErrorCode.PROCESS_TIMEOUT, "timed out")

    with pytest.raises(ProcessProtocolError) as timeout:
        env.step(0)
    assert timeout.value.code is ProcessErrorCode.PROCESS_TIMEOUT
    assert FakeWorker.instances[0].closed is True

    with pytest.raises(ProcessProtocolError, match="usable"):
        env.step(0)
    FakeWorker.fail_with = None
    env.reset(seed=456, task_id=TASK_ID)
    assert len(FakeWorker.instances) == 2
    env.close()


def test_response_parser_rejects_learning_transition_fields() -> None:
    payload = _health(1, 10)
    payload["reward"] = 0.0
    with pytest.raises(ProcessProtocolError) as error:
        parse_process_response(payload)
    assert error.value.code is ProcessErrorCode.UNKNOWN_FIELD


def test_worker_rejects_non_protocol_stdout_and_becomes_unusable() -> None:
    script = "import sys; print('native debug on stdout', flush=True); sys.stdin.readline()"
    worker = _WorkerProcess([sys.executable, "-c", script], None, 1.0, 1024 * 1024)
    try:
        with pytest.raises(ProcessProtocolError) as error:
            worker.request(make_health_request(1))
        assert error.value.code is ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE
        assert worker.unusable is True
    finally:
        worker.close()


def test_worker_timeout_marks_process_unusable() -> None:
    script = "import sys; sys.stdin.readline(); import time; time.sleep(5)"
    worker = _WorkerProcess([sys.executable, "-c", script], None, 0.05, 1024 * 1024)
    try:
        with pytest.raises(ProcessProtocolError) as error:
            worker.request(make_health_request(1))
        assert error.value.code is ProcessErrorCode.PROCESS_TIMEOUT
        assert worker.unusable is True
    finally:
        worker.close()


def test_worker_eof_marks_process_unusable() -> None:
    worker = _WorkerProcess([sys.executable, "-c", "pass"], None, 1.0, 1024 * 1024)
    try:
        with pytest.raises(ProcessProtocolError) as error:
            worker.request(make_health_request(1))
        assert error.value.code is ProcessErrorCode.PROCESS_EXITED
        assert worker.unusable is True
    finally:
        worker.close()
