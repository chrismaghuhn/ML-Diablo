from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

PROTOCOL_VERSION = "dxai.bridge.v1"
OBSERVATION_VERSION = "dxai.observation.v1"
ACTION_VERSION = "dxai.action.v1"


class FaultCode(StrEnum):
    STARTUP = "STARTUP"
    PROTOCOL = "PROTOCOL"
    TIMEOUT = "TIMEOUT"
    ENGINE_CRASH = "ENGINE_CRASH"
    INVALID_STATE = "INVALID_STATE"
    INVALID_ACTION = "INVALID_ACTION"
    STALE_REQUEST = "STALE_REQUEST"
    ASSET = "ASSET"
    FIXTURE = "FIXTURE"
    INTERNAL = "INTERNAL"


@dataclass(frozen=True, slots=True)
class Handshake:
    protocol_version: str
    observation_version: str
    action_version: str
    adapter_revision: str
    engine_revision: str
    build_fingerprint: str
    supported_tasks: tuple[str, ...]
    capabilities: tuple[str, ...] = ()

    def validate(self) -> None:
        if self.protocol_version != PROTOCOL_VERSION:
            raise ValueError("unsupported bridge protocol")
        if self.observation_version != OBSERVATION_VERSION:
            raise ValueError("unsupported observation contract")
        if self.action_version != ACTION_VERSION:
            raise ValueError("unsupported action contract")
        if not self.adapter_revision or not self.engine_revision or not self.build_fingerprint:
            raise ValueError("adapter, engine and build fingerprints are required")
        if not self.supported_tasks or len(set(self.supported_tasks)) != len(self.supported_tasks):
            raise ValueError("supported tasks must be non-empty and unique")

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol_version": self.protocol_version,
            "observation_version": self.observation_version,
            "action_version": self.action_version,
            "adapter_revision": self.adapter_revision,
            "engine_revision": self.engine_revision,
            "build_fingerprint": self.build_fingerprint,
            "supported_tasks": list(self.supported_tasks),
            "capabilities": list(self.capabilities),
        }


@dataclass(frozen=True, slots=True)
class ResetRequest:
    request_id: int
    seed: int
    task_id: str
    protocol_version: str = PROTOCOL_VERSION
    options: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def validate(self) -> None:
        if self.protocol_version != PROTOCOL_VERSION:
            raise ValueError("unsupported bridge protocol")
        if self.request_id < 0 or self.seed < 0:
            raise ValueError("request_id and seed must be non-negative")
        if not self.task_id:
            raise ValueError("task_id is required")
        keys = [key for key, _ in self.options]
        if len(keys) != len(set(keys)):
            raise ValueError("reset option keys must be unique")

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol_version": self.protocol_version,
            "request_id": self.request_id,
            "seed": self.seed,
            "task_id": self.task_id,
            "options": {key: value for key, value in self.options},
        }


@dataclass(frozen=True, slots=True)
class StepRequest:
    request_id: int
    episode_id: str
    expected_step_id: int
    candidate_id: int
    protocol_version: str = PROTOCOL_VERSION

    def validate(self) -> None:
        if self.protocol_version != PROTOCOL_VERSION:
            raise ValueError("unsupported bridge protocol")
        if min(self.request_id, self.expected_step_id, self.candidate_id) < 0:
            raise ValueError("request and step identifiers must be non-negative")
        if not self.episode_id:
            raise ValueError("episode_id is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol_version": self.protocol_version,
            "request_id": self.request_id,
            "episode_id": self.episode_id,
            "expected_step_id": self.expected_step_id,
            "candidate_id": self.candidate_id,
        }
