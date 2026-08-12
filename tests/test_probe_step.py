from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from dxai.contracts.observations import Observation
from dxai.env.legal import candidate_set_sha256
from dxai.env.probe import (
    ObservationProbe,
    ProbeError,
    ProbeErrorCode,
    ProbeStepResult,
    parse_probe_step,
)

ROOT = Path(__file__).parents[1]


def _payload() -> dict[str, object]:
    payload = json.loads(
        (ROOT / "schemas/examples/probe_step.example.json").read_text(encoding="utf-8")
    )
    observation = Observation.from_dict(payload["observation"])
    next_observation = Observation.from_dict(payload["next_observation"])
    payload["candidate_set_sha256"] = candidate_set_sha256(observation.legal_actions)
    payload["next_candidate_set_sha256"] = candidate_set_sha256(
        next_observation.legal_actions
    )
    return payload


def test_probe_step_parser_accepts_boundary_completion_without_target_reach() -> None:
    payload = _payload()
    result = parse_probe_step(json.dumps(payload))
    assert isinstance(result, ProbeStepResult)
    assert result.requested_target_reached is False
    assert result.observation.step_id == 0
    assert result.next_observation.step_id == 1


def test_probe_step_parser_binds_exact_candidate_set() -> None:
    payload = _payload()
    observation = Observation.from_dict(payload["observation"])
    payload["candidate_set_sha256"] = candidate_set_sha256(observation.legal_actions)
    next_observation = Observation.from_dict(payload["next_observation"])
    payload["next_candidate_set_sha256"] = candidate_set_sha256(next_observation.legal_actions)
    result = parse_probe_step(json.dumps(payload))
    assert result.candidate_set_sha256 == payload["candidate_set_sha256"]

    payload["candidate_set_sha256"] = "f" * 64
    with pytest.raises(ProbeError, match="candidate set"):
        parse_probe_step(json.dumps(payload))


def test_probe_step_parser_rejects_non_boolean_completion_flag() -> None:
    payload = _payload()
    payload["requested_target_reached"] = "false"
    with pytest.raises(ProbeError, match="must be boolean"):
        parse_probe_step(json.dumps(payload))


def test_new_native_failure_codes_are_structured() -> None:
    from dxai.env.probe import parse_probe_error

    for code in (
        ProbeErrorCode.CANDIDATE_REJECTED,
        ProbeErrorCode.STATE_MISMATCH,
        ProbeErrorCode.NO_SUPPORTED_CANDIDATES,
        ProbeErrorCode.ACTION_RESOLUTION_FAILED,
        ProbeErrorCode.STALE_CANDIDATE,
    ):
        error = parse_probe_error(
            json.dumps({"error_code": code.value, "error_message": "test"})
        )
        assert error.code is code


def test_probe_session_rejects_invalid_and_reused_candidate_without_running_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "probe.exe"
    executable.touch()
    assets = tmp_path / "diablo"
    assets.mkdir()
    core_assets = tmp_path / "core-assets"
    core_assets.mkdir()
    calls: list[list[str]] = []
    start_payload = _payload()["observation"]
    step_payload = _payload()
    observation = Observation.from_dict(start_payload)
    step_payload["candidate_set_sha256"] = candidate_set_sha256(observation.legal_actions)
    step_payload["next_candidate_set_sha256"] = candidate_set_sha256(
        Observation.from_dict(step_payload["next_observation"]).legal_actions
    )

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        stdout = json.dumps(step_payload if "--candidate-id" in command else start_payload)
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    session = ObservationProbe(
        executable=executable,
        assets_path=assets,
        core_assets_path=core_assets,
    ).start(seed=123, task_id="combat.single_melee.v0")

    with pytest.raises(ProbeError) as invalid:
        session.step(99)
    assert invalid.value.code is ProbeErrorCode.CANDIDATE_REJECTED
    assert len(calls) == 1

    session.step(0)
    with pytest.raises(ProbeError) as reused:
        session.step(0)
    assert reused.value.code is ProbeErrorCode.STALE_CANDIDATE
    assert len(calls) == 2


def test_probe_step_command_contains_only_candidate_id_for_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "probe.exe"
    executable.touch()
    assets = tmp_path / "diablo"
    assets.mkdir()
    core_assets = tmp_path / "core-assets"
    core_assets.mkdir()
    start_payload = _payload()["observation"]
    step_payload = _payload()
    observation = Observation.from_dict(start_payload)
    step_payload["candidate_set_sha256"] = candidate_set_sha256(observation.legal_actions)
    step_payload["next_candidate_set_sha256"] = candidate_set_sha256(
        Observation.from_dict(step_payload["next_observation"]).legal_actions
    )
    commands: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        stdout = json.dumps(step_payload if "--candidate-id" in command else start_payload)
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    session = ObservationProbe(
        executable=executable,
        assets_path=assets,
        core_assets_path=core_assets,
    ).start(seed=123, task_id="combat.single_melee.v0")
    session.step(0)
    command = commands[-1]
    assert "--candidate-id" in command
    assert "--target-tile" not in command
    assert "--mouse-x" not in command
