from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from dxai.contracts.actions import ActionCandidate
from dxai.contracts.observations import Observation
from dxai.env.legal import candidate_set_sha256 as compute_candidate_set_sha256
from dxai.env.observability import validate_observable_move_candidates


class ProbeErrorCode(StrEnum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    UPSTREAM_COMMIT_MISMATCH = "UPSTREAM_COMMIT_MISMATCH"
    ASSET_DATA_UNAVAILABLE = "ASSET_DATA_UNAVAILABLE"
    ENGINE_INITIALIZATION_FAILED = "ENGINE_INITIALIZATION_FAILED"
    OBSERVATION_CONTRACT_FAILED = "OBSERVATION_CONTRACT_FAILED"
    CANDIDATE_REJECTED = "CANDIDATE_REJECTED"
    STATE_MISMATCH = "STATE_MISMATCH"
    NO_SUPPORTED_CANDIDATES = "NO_SUPPORTED_CANDIDATES"
    ACTION_RESOLUTION_FAILED = "ACTION_RESOLUTION_FAILED"
    STALE_CANDIDATE = "STALE_CANDIDATE"
    TIMEOUT = "TIMEOUT"
    INTERNAL = "INTERNAL"


class ProbeError(RuntimeError):
    def __init__(self, code: ProbeErrorCode, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def parse_probe_error(stderr: str) -> ProbeError:
    for line in reversed(stderr.splitlines()):
        candidate = line.strip()
        if not candidate:
            continue
        try:
            payload: Any = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        code_value = payload.get("error_code")
        message_value = payload.get("error_message")
        if not isinstance(code_value, str) or not isinstance(message_value, str):
            continue
        try:
            code = ProbeErrorCode(code_value)
        except ValueError:
            code = ProbeErrorCode.INTERNAL
        return ProbeError(code, message_value)
    return ProbeError(ProbeErrorCode.INTERNAL, "probe exited without a structured error")


def parse_probe_observation(stdout: str) -> Observation:
    try:
        payload: Any = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise ProbeError(
            ProbeErrorCode.OBSERVATION_CONTRACT_FAILED,
            "probe stdout is not valid JSON",
        ) from error
    if not isinstance(payload, dict):
        raise ProbeError(
            ProbeErrorCode.OBSERVATION_CONTRACT_FAILED,
            "probe stdout must contain one JSON object",
        )
    try:
        return Observation.from_dict(payload)
    except (KeyError, TypeError, ValueError) as error:
        raise ProbeError(ProbeErrorCode.OBSERVATION_CONTRACT_FAILED, str(error)) from error


@dataclass(frozen=True, slots=True)
class ProbeStepResult:
    observation: Observation
    action: ActionCandidate
    next_observation: Observation
    candidate_set_sha256: str
    next_candidate_set_sha256: str
    requested_target_reached: bool

    def validate(self) -> None:
        self.observation.validate()
        self.next_observation.validate()
        validate_observable_move_candidates(self.observation)
        validate_observable_move_candidates(self.next_observation)
        if self.next_observation.episode_id != self.observation.episode_id:
            raise ValueError("probe step changed episode_id")
        if self.next_observation.task_id != self.observation.task_id:
            raise ValueError("probe step changed task_id")
        if self.next_observation.seed != self.observation.seed:
            raise ValueError("probe step changed seed")
        if self.next_observation.step_id != self.observation.step_id + 1:
            raise ValueError("probe step did not advance exactly one semantic step")
        if self.next_observation.engine_tick <= self.observation.engine_tick:
            raise ValueError("probe step did not advance engine logic")
        try:
            issued_action = self.observation.action_by_id(self.action.candidate_id)
        except KeyError as error:
            raise ValueError("probe step action is not in the issued candidate set") from error
        if issued_action != self.action:
            raise ValueError("probe step action differs from the issued candidate")
        if self.candidate_set_sha256 != compute_candidate_set_sha256(
            self.observation.legal_actions
        ):
            raise ValueError("initial candidate set digest does not match observation")
        if self.next_candidate_set_sha256 != compute_candidate_set_sha256(
            self.next_observation.legal_actions
        ):
            raise ValueError("next candidate set digest does not match observation")
        if not isinstance(self.requested_target_reached, bool):
            raise ValueError("requested_target_reached must be boolean")


def parse_probe_step(stdout: str | dict[str, Any]) -> ProbeStepResult:
    if isinstance(stdout, dict):
        payload: Any = stdout
    else:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as error:
            raise ProbeError(
                ProbeErrorCode.OBSERVATION_CONTRACT_FAILED,
                "probe stdout is not valid JSON",
            ) from error
    if not isinstance(payload, dict):
        raise ProbeError(
            ProbeErrorCode.OBSERVATION_CONTRACT_FAILED,
            "probe stdout must contain one JSON object",
        )
    try:
        if payload.get("schema_version") != "dxai.probe.step.v1":
            raise ValueError("unsupported probe step schema version")
        observation_value = payload["observation"]
        action_value = payload["action"]
        next_observation_value = payload["next_observation"]
        if not isinstance(observation_value, dict):
            raise TypeError("probe step observation must be an object")
        if not isinstance(action_value, dict):
            raise TypeError("probe step action must be an object")
        if not isinstance(next_observation_value, dict):
            raise TypeError("probe step next_observation must be an object")
        result = ProbeStepResult(
            observation=Observation.from_dict(observation_value),
            action=ActionCandidate.from_dict(action_value),
            next_observation=Observation.from_dict(next_observation_value),
            candidate_set_sha256=_required_digest(payload, "candidate_set_sha256"),
            next_candidate_set_sha256=_required_digest(payload, "next_candidate_set_sha256"),
            requested_target_reached=_required_bool(payload, "requested_target_reached"),
        )
        if result.observation.episode_id != payload.get("episode_id"):
            raise ValueError("probe step episode_id does not match observation")
        if result.observation.task_id != payload.get("task_id"):
            raise ValueError("probe step task_id does not match observation")
        if result.observation.seed != int(payload.get("seed", -1)):
            raise ValueError("probe step seed does not match observation")
        if result.observation.step_id != int(payload.get("step_id", -1)):
            raise ValueError("probe step step_id does not match observation")
        result.validate()
        return result
    except (KeyError, TypeError, ValueError) as error:
        raise ProbeError(ProbeErrorCode.OBSERVATION_CONTRACT_FAILED, str(error)) from error


def _required_digest(payload: dict[str, Any], field: str) -> str:
    value = payload[field]
    if not isinstance(value, str) or len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError(f"{field} must be a lowercase SHA-256 hex digest")
    return value


def _required_bool(payload: dict[str, Any], field: str) -> bool:
    value = payload[field]
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be boolean")
    return value


@dataclass(slots=True)
class ProbeSession:
    """The intentionally single-use M0.3 state surface.

    The native probe is still one-shot rather than a persistent IPC server. The
    next observation is returned as evidence of the next boundary, but it is not
    exposed as a second executable session in this milestone.
    """

    _probe: ObservationProbe
    seed: int
    task_id: str
    observation: Observation
    candidate_set_sha256: str
    _consumed: bool = False

    def step(self, candidate_id: int) -> ProbeStepResult:
        if self._consumed:
            raise ProbeError(
                ProbeErrorCode.STALE_CANDIDATE,
                "M0.3 probe sessions accept exactly one step",
            )
        try:
            self.observation.action_by_id(candidate_id)
        except (KeyError, TypeError) as error:
            raise ProbeError(
                ProbeErrorCode.CANDIDATE_REJECTED,
                f"candidate {candidate_id} is not legal for step {self.observation.step_id}",
            ) from error
        self._consumed = True
        return self._probe._execute_first_step(self, candidate_id)


@dataclass(frozen=True, slots=True)
class ObservationProbe:
    executable: Path
    assets_path: Path
    core_assets_path: Path
    engine_runtime_path: Path | None = None
    runtime_root: Path | None = None
    timeout_seconds: float = 60.0

    def read(self, *, seed: int, task_id: str) -> Observation:
        """Read the byte-compatible M0.2 observation mode."""

        return self._read_observation(seed=seed, task_id=task_id, mode=None)

    def start(self, *, seed: int, task_id: str) -> ProbeSession:
        observation = self._read_observation(seed=seed, task_id=task_id, mode="m03")
        validate_observable_move_candidates(observation)
        return ProbeSession(
            _probe=self,
            seed=seed,
            task_id=task_id,
            observation=observation,
            candidate_set_sha256=compute_candidate_set_sha256(observation.legal_actions),
        )

    def _execute_first_step(self, state: ProbeSession, candidate_id: int) -> ProbeStepResult:
        command_options = (
            "--candidate-id",
            str(candidate_id),
            "--expected-episode-id",
            state.observation.episode_id,
            "--expected-step-id",
            str(state.observation.step_id),
            "--expected-candidate-set-sha256",
            state.candidate_set_sha256,
        )
        result = parse_probe_step(
            self._run_json(
                seed=state.seed,
                task_id=state.task_id,
                mode="m03",
                extra_options=command_options,
            )
        )
        if result.observation != state.observation:
            raise ProbeError(
                ProbeErrorCode.STATE_MISMATCH,
                "native regeneration differs from the issued observation",
            )
        if result.candidate_set_sha256 != state.candidate_set_sha256:
            raise ProbeError(
                ProbeErrorCode.STATE_MISMATCH,
                "native regeneration differs from the issued candidate set",
            )
        if result.action != state.observation.action_by_id(candidate_id):
            raise ProbeError(
                ProbeErrorCode.STATE_MISMATCH,
                "native action differs from the issued candidate",
            )
        return result

    def _read_observation(self, *, seed: int, task_id: str, mode: str | None) -> Observation:
        payload = self._run_json(seed=seed, task_id=task_id, mode=mode)
        try:
            observation = Observation.from_dict(payload)
            observation.validate()
            return observation
        except (KeyError, TypeError, ValueError) as error:
            raise ProbeError(ProbeErrorCode.OBSERVATION_CONTRACT_FAILED, str(error)) from error

    def _run_json(
        self,
        *,
        seed: int,
        task_id: str,
        mode: str | None,
        extra_options: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        if seed < 0 or seed > 0xFFFFFFFF:
            raise ProbeError(ProbeErrorCode.INVALID_ARGUMENT, "seed must fit in uint32_t")
        if not task_id:
            raise ProbeError(ProbeErrorCode.INVALID_ARGUMENT, "task_id is required")
        if not self.executable.is_file():
            raise ProbeError(
                ProbeErrorCode.INVALID_ARGUMENT,
                f"probe executable does not exist: {self.executable}",
            )
        if not self.assets_path.is_dir():
            raise ProbeError(
                ProbeErrorCode.ASSET_DATA_UNAVAILABLE,
                f"asset directory does not exist: {self.assets_path}",
            )
        if not self.core_assets_path.is_dir():
            raise ProbeError(
                ProbeErrorCode.ASSET_DATA_UNAVAILABLE,
                f"core asset directory does not exist: {self.core_assets_path}",
            )
        if self.engine_runtime_path is not None and not self.engine_runtime_path.is_dir():
            raise ProbeError(
                ProbeErrorCode.ENGINE_INITIALIZATION_FAILED,
                f"engine runtime directory does not exist: {self.engine_runtime_path}",
            )
        if self.engine_runtime_path is not None:
            shared_library = self.engine_runtime_path / "libdevilutionx_so.dll"
            if not shared_library.is_file():
                raise ProbeError(
                    ProbeErrorCode.ENGINE_INITIALIZATION_FAILED,
                    f"engine runtime library does not exist: {shared_library}",
                )
        if self.timeout_seconds <= 0:
            raise ProbeError(ProbeErrorCode.INVALID_ARGUMENT, "timeout_seconds must be positive")

        command = [
            str(self.executable),
            "--assets",
            str(self.assets_path),
            "--core-assets",
            str(self.core_assets_path),
            "--seed",
            str(seed),
            "--task",
            task_id,
        ]
        if mode is not None:
            command.extend(("--mode", mode))
        command.extend(extra_options)
        if self.runtime_root is not None:
            command.extend(("--runtime-root", str(self.runtime_root)))

        environment = None
        if self.engine_runtime_path is not None:
            environment = os.environ.copy()
            environment["PATH"] = os.pathsep.join(
                (str(self.engine_runtime_path), environment.get("PATH", ""))
            )

        try:
            result = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                check=False,
                env=environment,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            raise ProbeError(ProbeErrorCode.TIMEOUT, "observation probe timed out") from error
        if result.returncode != 0:
            raise parse_probe_error(result.stderr)
        try:
            payload: Any = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise ProbeError(
                ProbeErrorCode.OBSERVATION_CONTRACT_FAILED,
                "probe stdout is not valid JSON",
            ) from error
        if not isinstance(payload, dict):
            raise ProbeError(
                ProbeErrorCode.OBSERVATION_CONTRACT_FAILED,
                "probe stdout must contain one JSON object",
            )
        return payload
