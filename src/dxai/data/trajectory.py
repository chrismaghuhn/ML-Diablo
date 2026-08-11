from __future__ import annotations

import json
import math
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn

from dxai.contracts.actions import ActionCandidate
from dxai.contracts.observations import Observation
from dxai.contracts.results import StepResult
from dxai.contracts.serialization import canonical_json, sha256_file

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_CONTRACTS = {"observation", "transition", "action"}


@dataclass(frozen=True, slots=True)
class TransitionRecord:
    schema_version: str
    episode_id: str
    task_id: str
    seed: int
    step_id: int
    observation: Observation
    action: ActionCandidate
    reward: float
    next_observation: Observation
    terminated: bool
    truncated: bool
    info: dict[str, Any]
    behavior: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.schema_version != "dxai.transition.v1":
            raise ValueError("unsupported transition schema")
        self.observation.validate()
        self.next_observation.validate()
        self.action.validate()
        if not math.isfinite(self.reward):
            raise ValueError("transition reward must be finite")
        if self.terminated and self.truncated:
            raise ValueError("transition cannot be both terminated and truncated")
        if not isinstance(self.info, dict) or not isinstance(self.behavior, dict):
            raise ValueError("transition info and behavior must be dictionaries")
        if self.episode_id != self.observation.episode_id:
            raise ValueError("transition and observation episode IDs differ")
        if self.episode_id != self.next_observation.episode_id:
            raise ValueError("transition and next observation episode IDs differ")
        if (
            self.task_id != self.observation.task_id
            or self.task_id != self.next_observation.task_id
        ):
            raise ValueError("transition task IDs differ")
        if self.seed != self.observation.seed or self.seed != self.next_observation.seed:
            raise ValueError("transition seeds differ")
        if self.step_id != self.observation.step_id:
            raise ValueError("transition step_id must equal observation step_id")
        if self.next_observation.step_id != self.step_id + 1:
            raise ValueError("next observation must advance exactly one decision step")
        if self.next_observation.engine_tick < self.observation.engine_tick:
            raise ValueError("engine_tick must not move backwards")
        expected = self.observation.action_by_id(self.action.candidate_id)
        if expected != self.action:
            raise ValueError("recorded action does not exactly match the legal candidate")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "episode_id": self.episode_id,
            "task_id": self.task_id,
            "seed": self.seed,
            "step_id": self.step_id,
            "observation": self.observation.to_dict(),
            "action": self.action.to_dict(),
            "reward": self.reward,
            "next_observation": self.next_observation.to_dict(),
            "terminated": self.terminated,
            "truncated": self.truncated,
            "info": self.info,
            "behavior": self.behavior,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> TransitionRecord:
        result = cls(
            schema_version=str(value["schema_version"]),
            episode_id=str(value["episode_id"]),
            task_id=str(value["task_id"]),
            seed=int(value["seed"]),
            step_id=int(value["step_id"]),
            observation=Observation.from_dict(value["observation"]),
            action=ActionCandidate.from_dict(value["action"]),
            reward=float(value["reward"]),
            next_observation=Observation.from_dict(value["next_observation"]),
            terminated=bool(value["terminated"]),
            truncated=bool(value["truncated"]),
            info=dict(value.get("info", {})),
            behavior=dict(value.get("behavior", {})),
        )
        result.validate()
        return result


@dataclass(frozen=True, slots=True)
class EpisodeManifest:
    schema_version: str
    episode_id: str
    task_id: str
    seed: int
    agent_name: str
    data_source: str
    step_count: int
    total_reward: float
    outcome: str
    terminated: bool
    truncated: bool
    trajectory_file: str
    trajectory_sha256: str
    created_at_utc: str
    contract_versions: dict[str, str]
    engine: dict[str, Any]

    def validate(self) -> None:
        if self.schema_version != "dxai.episode_manifest.v1":
            raise ValueError("unsupported episode manifest schema")
        required_text = (
            self.episode_id,
            self.task_id,
            self.agent_name,
            self.data_source,
            self.outcome,
            self.created_at_utc,
        )
        if any(not value for value in required_text):
            raise ValueError("manifest text identifiers must be non-empty")
        if self.seed < 0 or self.step_count < 0:
            raise ValueError("manifest seed and step_count must be non-negative")
        if not math.isfinite(self.total_reward):
            raise ValueError("manifest total_reward must be finite")
        if self.terminated and self.truncated:
            raise ValueError("manifest cannot be both terminated and truncated")
        if self.step_count == 0 and (self.terminated or self.truncated):
            raise ValueError("empty manifest cannot be terminal or truncated")
        if (
            not self.trajectory_file
            or self.trajectory_file in {".", ".."}
            or "/" in self.trajectory_file
            or "\\" in self.trajectory_file
        ):
            raise ValueError("trajectory_file must be a safe file name")
        if _SHA256_RE.fullmatch(self.trajectory_sha256) is None:
            raise ValueError("trajectory_sha256 must be a lowercase SHA-256 digest")
        if not _REQUIRED_CONTRACTS.issubset(self.contract_versions):
            raise ValueError("manifest is missing required contract versions")
        if any(not key or not value for key, value in self.contract_versions.items()):
            raise ValueError("contract version keys and values must be non-empty")
        try:
            created_at = datetime.fromisoformat(self.created_at_utc)
        except ValueError as error:
            raise ValueError("created_at_utc must be ISO-8601") from error
        if created_at.tzinfo is None:
            raise ValueError("created_at_utc must include a timezone")
        if not isinstance(self.engine, dict):
            raise ValueError("engine metadata must be a dictionary")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "episode_id": self.episode_id,
            "task_id": self.task_id,
            "seed": self.seed,
            "agent_name": self.agent_name,
            "data_source": self.data_source,
            "step_count": self.step_count,
            "total_reward": self.total_reward,
            "outcome": self.outcome,
            "terminated": self.terminated,
            "truncated": self.truncated,
            "trajectory_file": self.trajectory_file,
            "trajectory_sha256": self.trajectory_sha256,
            "created_at_utc": self.created_at_utc,
            "contract_versions": self.contract_versions,
            "engine": self.engine,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> EpisodeManifest:
        result = cls(
            schema_version=str(value["schema_version"]),
            episode_id=str(value["episode_id"]),
            task_id=str(value["task_id"]),
            seed=int(value["seed"]),
            agent_name=str(value["agent_name"]),
            data_source=str(value["data_source"]),
            step_count=int(value["step_count"]),
            total_reward=float(value["total_reward"]),
            outcome=str(value["outcome"]),
            terminated=bool(value["terminated"]),
            truncated=bool(value["truncated"]),
            trajectory_file=str(value["trajectory_file"]),
            trajectory_sha256=str(value["trajectory_sha256"]),
            created_at_utc=str(value["created_at_utc"]),
            contract_versions=dict(value["contract_versions"]),
            engine=dict(value.get("engine", {})),
        )
        result.validate()
        return result


class EpisodeRecorder:
    """Atomic JSONL recorder with an integrity manifest."""

    def __init__(
        self,
        root: Path,
        initial_observation: Observation,
        *,
        agent_name: str,
        data_source: str = "AGENT",
        engine: dict[str, Any] | None = None,
    ) -> None:
        initial_observation.validate()
        self._initial = initial_observation
        self._directory = root / initial_observation.episode_id
        self._directory.mkdir(parents=True, exist_ok=False)
        self._tmp_path = self._directory / "transitions.jsonl.tmp"
        self._final_path = self._directory / "transitions.jsonl"
        self._manifest_path = self._directory / "manifest.json"
        self._manifest_tmp_path = self._directory / "manifest.json.tmp"
        self._stream = self._tmp_path.open("w", encoding="utf-8", newline="\n")
        self._agent_name = agent_name
        self._data_source = data_source
        self._engine = engine or {"name": "dxai.mock", "revision": "v1"}
        self._step_count = 0
        self._total_reward = 0.0
        self._last_result: StepResult | None = None
        self._closed = False

    @property
    def directory(self) -> Path:
        return self._directory

    def record(
        self,
        observation: Observation,
        candidate_id: int,
        result: StepResult,
        *,
        behavior: dict[str, Any] | None = None,
    ) -> TransitionRecord:
        if self._closed:
            raise RuntimeError("recorder is closed")
        result.validate()
        if observation.step_id != self._step_count:
            raise ValueError("recorder expects contiguous decision steps")
        action = observation.action_by_id(candidate_id)
        record = TransitionRecord(
            schema_version="dxai.transition.v1",
            episode_id=observation.episode_id,
            task_id=observation.task_id,
            seed=observation.seed,
            step_id=observation.step_id,
            observation=observation,
            action=action,
            reward=result.reward,
            next_observation=result.observation,
            terminated=result.terminated,
            truncated=result.truncated,
            info=result.info,
            behavior=behavior or {},
        )
        record.validate()
        self._stream.write(canonical_json(record.to_dict()))
        self._stream.write("\n")
        self._step_count += 1
        self._total_reward += result.reward
        self._last_result = result
        return record

    def close(self) -> EpisodeManifest:
        if self._closed:
            raise RuntimeError("recorder is already closed")
        try:
            self._stream.flush()
            os.fsync(self._stream.fileno())
            self._stream.close()
            os.replace(self._tmp_path, self._final_path)
            final = self._last_result
            terminated = False if final is None else final.terminated
            truncated = False if final is None else final.truncated
            outcome = "EMPTY" if final is None else str(final.info.get("outcome", "UNKNOWN"))
            manifest = EpisodeManifest(
                schema_version="dxai.episode_manifest.v1",
                episode_id=self._initial.episode_id,
                task_id=self._initial.task_id,
                seed=self._initial.seed,
                agent_name=self._agent_name,
                data_source=self._data_source,
                step_count=self._step_count,
                total_reward=self._total_reward,
                outcome=outcome,
                terminated=terminated,
                truncated=truncated,
                trajectory_file=self._final_path.name,
                trajectory_sha256=sha256_file(self._final_path),
                created_at_utc=datetime.now(UTC).isoformat(),
                contract_versions={
                    "observation": "dxai.observation.v1",
                    "transition": "dxai.transition.v1",
                    "action": "dxai.action.v1",
                },
                engine=self._engine,
            )
            manifest.validate()
            with self._manifest_tmp_path.open("w", encoding="utf-8", newline="\n") as stream:
                stream.write(canonical_json(manifest.to_dict()) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(self._manifest_tmp_path, self._manifest_path)
            self._closed = True
            return manifest
        except BaseException:
            self._discard_invalid_episode()
            self._closed = True
            raise

    def abort(self) -> None:
        """Discard an incomplete episode so collectors cannot ingest it as valid data."""
        if self._closed:
            return
        self._discard_invalid_episode()
        self._closed = True

    def _discard_invalid_episode(self) -> None:
        if not self._stream.closed:
            self._stream.close()
        for path in (
            self._tmp_path,
            self._final_path,
            self._manifest_tmp_path,
            self._manifest_path,
        ):
            path.unlink(missing_ok=True)
        try:
            self._directory.rmdir()
        except OSError:
            pass

    def __enter__(self) -> EpisodeRecorder:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if exc_type is None:
            if not self._closed:
                self.close()
        else:
            self.abort()


def read_episode(
    directory: Path,
    *,
    verify_checksum: bool = True,
) -> tuple[EpisodeManifest, list[TransitionRecord]]:
    manifest_path = directory / "manifest.json"
    manifest = EpisodeManifest.from_dict(_loads_strict(manifest_path.read_text(encoding="utf-8")))
    trajectory_path = directory / manifest.trajectory_file
    if verify_checksum and sha256_file(trajectory_path) != manifest.trajectory_sha256:
        raise ValueError("trajectory checksum mismatch")
    records = [
        TransitionRecord.from_dict(_loads_strict(line))
        for line in trajectory_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(records) != manifest.step_count:
        raise ValueError("manifest step count does not match trajectory")
    if records:
        if records[0].step_id != 0:
            raise ValueError("episode trajectory must start at step zero")
        if any(item.terminated or item.truncated for item in records[:-1]):
            raise ValueError("episode contains transitions after a terminal boundary")
        final = records[-1]
        if final.terminated != manifest.terminated or final.truncated != manifest.truncated:
            raise ValueError("manifest termination flags do not match trajectory")
        if str(final.info.get("outcome", "UNKNOWN")) != manifest.outcome:
            raise ValueError("manifest outcome does not match trajectory")
    elif manifest.outcome != "EMPTY":
        raise ValueError("empty trajectory must use outcome EMPTY")
    if abs(math.fsum(item.reward for item in records) - manifest.total_reward) > 1e-9:
        raise ValueError("manifest return does not match trajectory")
    return manifest, records


def iter_transition_dicts(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                value = _loads_strict(line)
                if not isinstance(value, dict):
                    raise ValueError("transition line must contain a JSON object")
                yield value


def _loads_strict(value: str) -> Any:
    return json.loads(value, parse_constant=_reject_non_json_number)


def _reject_non_json_number(value: str) -> NoReturn:
    raise ValueError(f"non-JSON numeric constant {value!r} is forbidden")
