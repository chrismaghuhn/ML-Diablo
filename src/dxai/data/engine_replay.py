from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

from dxai.contracts.actions import ActionCandidate, ActionKind
from dxai.contracts.common import Vec2
from dxai.contracts.serialization import canonical_json, canonical_json_bytes
from dxai.env.determinism import canonicalize_m04_trace
from dxai.env.legal import canonical_action_key
from dxai.protocol.lifecycle import (
    ADAPTER_REVISION,
    BUILD_FINGERPRINT,
    DEVILUTIONX_REVISION,
    PROCESS_PROTOCOL_VERSION,
    SUPPORTED_TASK_VERSIONS,
)
from dxai.protocol.messages import ACTION_VERSION, OBSERVATION_VERSION

ENGINE_REPLAY_SCHEMA_VERSION = "dxai.engine_replay.v1"
ENGINE_REPLAY_STEP_SCHEMA_VERSION = "dxai.engine_replay_step.v1"
CANDIDATE_CANONICALIZATION_VERSION = "dxai.candidate_set.v1"
ENGINE_REPLAY_STEPS_FILE = "steps.jsonl"

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SEMANTIC_ACTION_FIELDS = (
    "kind",
    "target_entity_id",
    "target_tile",
    "inventory_slot",
    "equipment_slot",
    "belt_slot",
    "spell_id",
    "store_item_id",
    "stat_id",
)
_STEP_FIELDS = frozenset(
    {
        "step_id",
        "observation_before_sha256",
        "candidate_set_before_sha256",
        "action",
        "action_canonical_key",
        "recorded_candidate_id",
        "observation_after_sha256",
        "candidate_set_after_sha256",
        "engine_tick_before",
        "engine_tick_after",
    }
)
_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "task_id",
        "seed",
        "step_count",
        "devilutionx_revision",
        "adapter_revision",
        "build_fingerprint",
        "process_protocol_version",
        "observation_version",
        "action_version",
        "candidate_canonicalization_version",
        "asset_set_fingerprint",
        "initial_observation_sha256",
        "initial_candidate_set_sha256",
        "final_observation_sha256",
        "semantic_trace_sha256",
        "steps_file",
        "steps_file_sha256",
    }
)


@dataclass(frozen=True, slots=True)
class SemanticAction:
    """The closed semantic payload of an action without local candidate data."""

    kind: ActionKind
    target_entity_id: int | None = None
    target_tile: Vec2 | None = None
    inventory_slot: int | None = None
    equipment_slot: int | None = None
    belt_slot: int | None = None
    spell_id: int | None = None
    store_item_id: int | None = None
    stat_id: int | None = None

    @classmethod
    def from_candidate(cls, action: ActionCandidate) -> SemanticAction:
        action.validate()
        return cls(
            kind=action.kind,
            target_entity_id=action.target_entity_id,
            target_tile=action.target_tile,
            inventory_slot=action.inventory_slot,
            equipment_slot=action.equipment_slot,
            belt_slot=action.belt_slot,
            spell_id=action.spell_id,
            store_item_id=action.store_item_id,
            stat_id=action.stat_id,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> SemanticAction:
        _require_exact_fields(value, _SEMANTIC_ACTION_FIELDS, "semantic action")
        tile_value = value["target_tile"]
        tile = None
        if tile_value is not None:
            _require_exact_fields(tile_value, {"x", "y"}, "target_tile")
            tile = Vec2(
                x=_require_int(tile_value["x"], "target_tile.x"),
                y=_require_int(tile_value["y"], "target_tile.y"),
            )
        result = cls(
            kind=_require_action_kind(value["kind"]),
            target_entity_id=_optional_int(value["target_entity_id"], "target_entity_id"),
            target_tile=tile,
            inventory_slot=_optional_int(value["inventory_slot"], "inventory_slot"),
            equipment_slot=_optional_int(value["equipment_slot"], "equipment_slot"),
            belt_slot=_optional_int(value["belt_slot"], "belt_slot"),
            spell_id=_optional_int(value["spell_id"], "spell_id"),
            store_item_id=_optional_int(value["store_item_id"], "store_item_id"),
            stat_id=_optional_int(value["stat_id"], "stat_id"),
        )
        result.validate()
        return result

    @property
    def canonical_key(self) -> str:
        return canonical_action_key(self.as_candidate())

    def as_candidate(self, candidate_id: int = 0) -> ActionCandidate:
        result = ActionCandidate(
            candidate_id=candidate_id,
            kind=self.kind,
            target_entity_id=self.target_entity_id,
            target_tile=self.target_tile,
            inventory_slot=self.inventory_slot,
            equipment_slot=self.equipment_slot,
            belt_slot=self.belt_slot,
            spell_id=self.spell_id,
            store_item_id=self.store_item_id,
            stat_id=self.stat_id,
        )
        result.validate()
        return result

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "kind": self.kind.value,
            "target_entity_id": self.target_entity_id,
            "target_tile": None if self.target_tile is None else self.target_tile.to_dict(),
            "inventory_slot": self.inventory_slot,
            "equipment_slot": self.equipment_slot,
            "belt_slot": self.belt_slot,
            "spell_id": self.spell_id,
            "store_item_id": self.store_item_id,
            "stat_id": self.stat_id,
        }

    def validate(self) -> None:
        ActionCandidate(
            candidate_id=0,
            kind=self.kind,
            target_entity_id=self.target_entity_id,
            target_tile=self.target_tile,
            inventory_slot=self.inventory_slot,
            equipment_slot=self.equipment_slot,
            belt_slot=self.belt_slot,
            spell_id=self.spell_id,
            store_item_id=self.store_item_id,
            stat_id=self.stat_id,
        ).validate()


@dataclass(frozen=True, slots=True)
class EngineReplayStep:
    step_id: int
    observation_before_sha256: str
    candidate_set_before_sha256: str
    action: SemanticAction
    action_canonical_key: str
    recorded_candidate_id: int
    observation_after_sha256: str
    candidate_set_after_sha256: str
    engine_tick_before: int
    engine_tick_after: int

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> EngineReplayStep:
        _require_exact_fields(value, _STEP_FIELDS, "engine replay step")
        result = cls(
            step_id=_require_int(value["step_id"], "step_id"),
            observation_before_sha256=_require_hash(
                value["observation_before_sha256"], "observation_before_sha256"
            ),
            candidate_set_before_sha256=_require_hash(
                value["candidate_set_before_sha256"], "candidate_set_before_sha256"
            ),
            action=SemanticAction.from_dict(value["action"]),
            action_canonical_key=_require_string(
                value["action_canonical_key"], "action_canonical_key"
            ),
            recorded_candidate_id=_require_int(
                value["recorded_candidate_id"], "recorded_candidate_id"
            ),
            observation_after_sha256=_require_hash(
                value["observation_after_sha256"], "observation_after_sha256"
            ),
            candidate_set_after_sha256=_require_hash(
                value["candidate_set_after_sha256"], "candidate_set_after_sha256"
            ),
            engine_tick_before=_require_int(value["engine_tick_before"], "engine_tick_before"),
            engine_tick_after=_require_int(value["engine_tick_after"], "engine_tick_after"),
        )
        result.validate()
        return result

    def semantic_dict(self) -> dict[str, Any]:
        value = self.to_dict()
        value.pop("recorded_candidate_id")
        return value

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "step_id": self.step_id,
            "observation_before_sha256": self.observation_before_sha256,
            "candidate_set_before_sha256": self.candidate_set_before_sha256,
            "action": self.action.to_dict(),
            "action_canonical_key": self.action_canonical_key,
            "recorded_candidate_id": self.recorded_candidate_id,
            "observation_after_sha256": self.observation_after_sha256,
            "candidate_set_after_sha256": self.candidate_set_after_sha256,
            "engine_tick_before": self.engine_tick_before,
            "engine_tick_after": self.engine_tick_after,
        }

    def validate(self) -> None:
        _require_nonnegative_int(self.step_id, "step_id")
        _require_nonnegative_int(self.recorded_candidate_id, "recorded_candidate_id")
        _require_nonnegative_int(self.engine_tick_before, "engine_tick_before")
        _require_nonnegative_int(self.engine_tick_after, "engine_tick_after")
        if self.engine_tick_after < self.engine_tick_before:
            raise ValueError("engine ticks must be non-decreasing")
        self.action.validate()
        if self.action_canonical_key != self.action.canonical_key:
            raise ValueError("action canonical key does not match semantic action")
        for name in (
            "observation_before_sha256",
            "candidate_set_before_sha256",
            "observation_after_sha256",
            "candidate_set_after_sha256",
        ):
            _require_hash(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class EngineReplayManifest:
    schema_version: str
    task_id: str
    seed: int
    step_count: int
    devilutionx_revision: str
    adapter_revision: str
    build_fingerprint: str
    process_protocol_version: str
    observation_version: str
    action_version: str
    candidate_canonicalization_version: str
    asset_set_fingerprint: str
    initial_observation_sha256: str
    initial_candidate_set_sha256: str
    final_observation_sha256: str
    semantic_trace_sha256: str
    steps_file: str
    steps_file_sha256: str

    @classmethod
    def create(
        cls,
        *,
        task_id: str,
        seed: int,
        devilutionx_revision: str,
        adapter_revision: str,
        build_fingerprint: str,
        asset_set_fingerprint: str,
        initial_observation_sha256: str,
        initial_candidate_set_sha256: str,
        steps: Iterable[EngineReplayStep],
    ) -> EngineReplayManifest:
        materialized = tuple(steps)
        _validate_steps(materialized)
        serialized_steps = serialize_steps(materialized)
        result = cls(
            schema_version=ENGINE_REPLAY_SCHEMA_VERSION,
            task_id=task_id,
            seed=seed,
            step_count=len(materialized),
            devilutionx_revision=devilutionx_revision,
            adapter_revision=adapter_revision,
            build_fingerprint=build_fingerprint,
            process_protocol_version=PROCESS_PROTOCOL_VERSION,
            observation_version=OBSERVATION_VERSION,
            action_version=ACTION_VERSION,
            candidate_canonicalization_version=CANDIDATE_CANONICALIZATION_VERSION,
            asset_set_fingerprint=asset_set_fingerprint,
            initial_observation_sha256=initial_observation_sha256,
            initial_candidate_set_sha256=initial_candidate_set_sha256,
            final_observation_sha256=materialized[-1].observation_after_sha256,
            semantic_trace_sha256=semantic_trace_sha256(materialized),
            steps_file=ENGINE_REPLAY_STEPS_FILE,
            steps_file_sha256=hashlib.sha256(serialized_steps).hexdigest(),
        )
        result.validate()
        _validate_manifest_steps(result, materialized)
        return result

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> EngineReplayManifest:
        _require_exact_fields(value, _MANIFEST_FIELDS, "engine replay manifest")
        result = cls(
            schema_version=_require_string(value["schema_version"], "schema_version"),
            task_id=_require_string(value["task_id"], "task_id"),
            seed=_require_int(value["seed"], "seed"),
            step_count=_require_int(value["step_count"], "step_count"),
            devilutionx_revision=_require_string(
                value["devilutionx_revision"], "devilutionx_revision"
            ),
            adapter_revision=_require_string(value["adapter_revision"], "adapter_revision"),
            build_fingerprint=_require_string(
                value["build_fingerprint"], "build_fingerprint"
            ),
            process_protocol_version=_require_string(
                value["process_protocol_version"], "process_protocol_version"
            ),
            observation_version=_require_string(
                value["observation_version"], "observation_version"
            ),
            action_version=_require_string(value["action_version"], "action_version"),
            candidate_canonicalization_version=_require_string(
                value["candidate_canonicalization_version"],
                "candidate_canonicalization_version",
            ),
            asset_set_fingerprint=_require_string(
                value["asset_set_fingerprint"], "asset_set_fingerprint"
            ),
            initial_observation_sha256=_require_hash(
                value["initial_observation_sha256"], "initial_observation_sha256"
            ),
            initial_candidate_set_sha256=_require_hash(
                value["initial_candidate_set_sha256"], "initial_candidate_set_sha256"
            ),
            final_observation_sha256=_require_hash(
                value["final_observation_sha256"], "final_observation_sha256"
            ),
            semantic_trace_sha256=_require_hash(
                value["semantic_trace_sha256"], "semantic_trace_sha256"
            ),
            steps_file=_require_string(value["steps_file"], "steps_file"),
            steps_file_sha256=_require_hash(value["steps_file_sha256"], "steps_file_sha256"),
        )
        result.validate()
        return result

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "seed": self.seed,
            "step_count": self.step_count,
            "devilutionx_revision": self.devilutionx_revision,
            "adapter_revision": self.adapter_revision,
            "build_fingerprint": self.build_fingerprint,
            "process_protocol_version": self.process_protocol_version,
            "observation_version": self.observation_version,
            "action_version": self.action_version,
            "candidate_canonicalization_version": self.candidate_canonicalization_version,
            "asset_set_fingerprint": self.asset_set_fingerprint,
            "initial_observation_sha256": self.initial_observation_sha256,
            "initial_candidate_set_sha256": self.initial_candidate_set_sha256,
            "final_observation_sha256": self.final_observation_sha256,
            "semantic_trace_sha256": self.semantic_trace_sha256,
            "steps_file": self.steps_file,
            "steps_file_sha256": self.steps_file_sha256,
        }

    def validate(self) -> None:
        if self.schema_version != ENGINE_REPLAY_SCHEMA_VERSION:
            raise ValueError("unsupported engine replay version")
        if self.process_protocol_version != PROCESS_PROTOCOL_VERSION:
            raise ValueError("incompatible process protocol version")
        if self.observation_version != OBSERVATION_VERSION:
            raise ValueError("incompatible observation version")
        if self.action_version != ACTION_VERSION:
            raise ValueError("incompatible action version")
        if self.candidate_canonicalization_version != CANDIDATE_CANONICALIZATION_VERSION:
            raise ValueError("incompatible candidate canonicalization version")
        if not self.task_id:
            raise ValueError("task_id is required")
        if self.task_id not in SUPPORTED_TASK_VERSIONS:
            raise ValueError(f"incompatible task_id: {self.task_id}")
        _require_uint32(self.seed, "seed")
        if self.step_count < 1:
            raise ValueError("step_count must be positive")
        for name, expected in (
            ("devilutionx_revision", DEVILUTIONX_REVISION),
            ("adapter_revision", ADAPTER_REVISION),
            ("build_fingerprint", BUILD_FINGERPRINT),
        ):
            _require_string(getattr(self, name), name)
            if getattr(self, name) != expected:
                raise ValueError(f"incompatible {name}: expected {expected!r}")
        _validate_asset_fingerprint(self.asset_set_fingerprint)
        for name in (
            "initial_observation_sha256",
            "initial_candidate_set_sha256",
            "final_observation_sha256",
            "semantic_trace_sha256",
            "steps_file_sha256",
        ):
            _require_hash(getattr(self, name), name)
        if self.steps_file != ENGINE_REPLAY_STEPS_FILE:
            raise ValueError("steps_file must be the safe literal steps.jsonl")


def semantic_trace_sha256(steps: Iterable[EngineReplayStep]) -> str:
    materialized = tuple(steps)
    _validate_steps(materialized)
    value = [canonicalize_m04_trace(step.semantic_dict()) for step in materialized]
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def serialize_steps(steps: Iterable[EngineReplayStep]) -> bytes:
    materialized = tuple(steps)
    _validate_steps(materialized)
    return b"".join(canonical_json(step.to_dict()).encode("utf-8") + b"\n" for step in materialized)


def publish_engine_replay(
    directory: Path, manifest: EngineReplayManifest, steps: Iterable[EngineReplayStep]
) -> None:
    materialized = tuple(steps)
    manifest.validate()
    _validate_manifest_steps(manifest, materialized)
    serialized_steps = serialize_steps(materialized)

    destination = Path(directory)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"replay destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.parent / f".{destination.name}.tmp-{uuid.uuid4().hex}"
    temporary.mkdir()
    try:
        temporary_steps = temporary / f"{ENGINE_REPLAY_STEPS_FILE}.tmp"
        final_steps = temporary / ENGINE_REPLAY_STEPS_FILE
        _write_fsync(temporary_steps, serialized_steps)
        os.replace(temporary_steps, final_steps)

        temporary_manifest = temporary / "manifest.json.tmp"
        final_manifest = temporary / "manifest.json"
        _write_fsync(
            temporary_manifest,
            canonical_json(manifest.to_dict()).encode("utf-8") + b"\n",
        )
        os.replace(temporary_manifest, final_manifest)
        _fsync_directory(temporary)
        os.replace(temporary, destination)
        _fsync_directory(destination.parent)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def load_engine_replay(
    directory: Path,
) -> tuple[EngineReplayManifest, tuple[EngineReplayStep, ...]]:
    root = Path(directory)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("replay directory must be a real directory")
    manifest_path = root / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("replay manifest is missing or is a symlink")
    manifest = EngineReplayManifest.from_dict(_load_json_object(manifest_path))
    entries = tuple(root.iterdir())
    if any(entry.is_symlink() for entry in entries):
        raise ValueError("replay artifact contains a symlink")
    allowed_names = {"manifest.json", manifest.steps_file}
    unexpected_names = sorted(entry.name for entry in entries if entry.name not in allowed_names)
    if unexpected_names:
        raise ValueError(
            f"replay artifact contains unexpected file: {unexpected_names[0]}"
        )
    steps_path = root / manifest.steps_file
    if steps_path.is_symlink() or not steps_path.is_file():
        raise ValueError("replay steps file is missing or is a symlink")
    steps_bytes = steps_path.read_bytes()
    if hashlib.sha256(steps_bytes).hexdigest() != manifest.steps_file_sha256:
        raise ValueError("steps checksum mismatch")
    steps: list[EngineReplayStep] = []
    for line_number, line in enumerate(steps_bytes.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"blank replay step at line {line_number}")
        value = _loads_strict(line)
        if not isinstance(value, dict):
            raise ValueError(f"replay step at line {line_number} must be an object")
        steps.append(EngineReplayStep.from_dict(value))
    _validate_manifest_steps(manifest, tuple(steps))
    return manifest, tuple(steps)


def validate_engine_replay(
    manifest: EngineReplayManifest, steps: Iterable[EngineReplayStep]
) -> tuple[EngineReplayStep, ...]:
    materialized = tuple(steps)
    manifest.validate()
    _validate_manifest_steps(manifest, materialized)
    return materialized


def _validate_manifest_steps(
    manifest: EngineReplayManifest, steps: tuple[EngineReplayStep, ...]
) -> None:
    _validate_steps(steps)
    if manifest.step_count != len(steps):
        raise ValueError("manifest step count does not match steps")
    if steps[0].observation_before_sha256 != manifest.initial_observation_sha256:
        raise ValueError("manifest initial observation hash does not match steps")
    if steps[0].candidate_set_before_sha256 != manifest.initial_candidate_set_sha256:
        raise ValueError("manifest initial candidate-set hash does not match steps")
    if steps[-1].observation_after_sha256 != manifest.final_observation_sha256:
        raise ValueError("manifest final observation hash does not match steps")
    if manifest.semantic_trace_sha256 != semantic_trace_sha256(steps):
        raise ValueError("manifest semantic trace checksum mismatch")
    if manifest.steps_file_sha256 != hashlib.sha256(serialize_steps(steps)).hexdigest():
        raise ValueError("manifest steps checksum mismatch")


def _validate_steps(steps: tuple[EngineReplayStep, ...]) -> None:
    if not steps:
        raise ValueError("engine replay must contain at least one step")
    for expected_id, step in enumerate(steps):
        step.validate()
        if step.step_id != expected_id:
            raise ValueError("replay step IDs must be contiguous from zero")


def _load_json_object(path: Path) -> dict[str, Any]:
    value = _loads_strict(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _loads_strict(value: str) -> Any:
    try:
        return json.loads(
            value,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_json_number,
        )
    except (TypeError, ValueError, UnicodeDecodeError) as error:
        if isinstance(error, ValueError) and str(error):
            raise
        raise ValueError("malformed replay JSON") from error


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_non_json_number(value: str) -> NoReturn:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def _require_exact_fields(
    value: Mapping[str, Any], expected: Iterable[str], name: str
) -> None:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    actual = set(value)
    expected_fields = set(expected)
    missing = sorted(expected_fields - actual)
    unknown = sorted(actual - expected_fields)
    if missing:
        raise ValueError(f"{name} missing field(s): {', '.join(missing)}")
    if unknown:
        raise ValueError(f"{name} has unknown field(s): {', '.join(unknown)}")


def _require_action_kind(value: Any) -> ActionKind:
    if not isinstance(value, str):
        raise ValueError("action kind must be a string")
    try:
        return ActionKind(value)
    except ValueError as error:
        raise ValueError(f"unsupported action kind: {value}") from error


def _require_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _require_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _optional_int(value: Any, name: str) -> int | None:
    if value is None:
        return None
    result = _require_int(value, name)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _require_nonnegative_int(value: Any, name: str) -> int:
    result = _require_int(value, name)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _require_uint32(value: Any, name: str) -> int:
    result = _require_nonnegative_int(value, name)
    if result > (1 << 32) - 1:
        raise ValueError(f"{name} must fit in uint32")
    return result


def _require_hash(value: Any, name: str) -> str:
    result = _require_string(value, name)
    if _HASH_PATTERN.fullmatch(result) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return result


def _validate_asset_fingerprint(value: Any) -> None:
    result = _require_string(value, "asset_set_fingerprint")
    if len(result) > 256 or any(token in result for token in ("/", "\\", ":", "..")):
        raise ValueError("asset_set_fingerprint must be a non-path identity")


def _write_fsync(path: Path, data: bytes) -> None:
    with path.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(str(path), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)
