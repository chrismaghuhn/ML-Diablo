from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from dxai.contracts.actions import ActionCandidate
from dxai.contracts.observations import Observation
from dxai.protocol.messages import ACTION_VERSION, OBSERVATION_VERSION

PROCESS_PROTOCOL_VERSION = "dxai.process.v1"
ADAPTER_REVISION = "m0.4"
DEVILUTIONX_REVISION = "07385842840437cc9a785b195f5b40b121eaeb1c"
BUILD_FINGERPRINT = "dxai-ml-diablo-m0.4"
SUPPORTED_TASK_VERSIONS = ("combat.single_melee.v0",)
SUPPORTED_FEATURES = ("MOVE_TO_TILE", "cold_reset", "request_idempotency")
MAX_UINT32 = (1 << 32) - 1
MAX_UINT64 = (1 << 64) - 1
MAX_REQUEST_CACHE_ENTRIES = 128


class ProcessState(StrEnum):
    READY = "READY"
    EPISODE_ACTIVE = "EPISODE_ACTIVE"
    FAULTED = "FAULTED"


class ProcessErrorCode(StrEnum):
    MALFORMED_UTF8 = "MALFORMED_UTF8"
    MALFORMED_JSON = "MALFORMED_JSON"
    OVERSIZED_FRAME = "OVERSIZED_FRAME"
    UNKNOWN_MESSAGE_TYPE = "UNKNOWN_MESSAGE_TYPE"
    UNKNOWN_FIELD = "UNKNOWN_FIELD"
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_FIELD = "INVALID_FIELD"
    PROTOCOL_VERSION_MISMATCH = "PROTOCOL_VERSION_MISMATCH"
    REQUEST_ID_REUSE = "REQUEST_ID_REUSE"
    REQUEST_ID_EXPIRED = "REQUEST_ID_EXPIRED"
    INVALID_STATE = "INVALID_STATE"
    ENGINE_FAULTED = "ENGINE_FAULTED"
    STALE_EPISODE = "STALE_EPISODE"
    STALE_STEP = "STALE_STEP"
    STATE_MISMATCH = "STATE_MISMATCH"
    INVALID_CANDIDATE = "INVALID_CANDIDATE"
    NO_SUPPORTED_CANDIDATES = "NO_SUPPORTED_CANDIDATES"
    ENGINE_FAULT = "ENGINE_FAULT"
    ASSET_DATA_UNAVAILABLE = "ASSET_DATA_UNAVAILABLE"
    ENGINE_INITIALIZATION_FAILED = "ENGINE_INITIALIZATION_FAILED"
    OBSERVATION_CONTRACT_FAILED = "OBSERVATION_CONTRACT_FAILED"
    CANDIDATE_REJECTED = "CANDIDATE_REJECTED"
    ACTION_RESOLUTION_FAILED = "ACTION_RESOLUTION_FAILED"
    STALE_CANDIDATE = "STALE_CANDIDATE"
    PROCESS_EXITED = "PROCESS_EXITED"
    PROCESS_TIMEOUT = "PROCESS_TIMEOUT"
    PROTOCOL_MALFORMED_RESPONSE = "PROTOCOL_MALFORMED_RESPONSE"
    PROCESS_VERSION_MISMATCH = "PROCESS_VERSION_MISMATCH"
    STARTUP = "STARTUP"
    PROTOCOL = "PROTOCOL"
    TIMEOUT = "TIMEOUT"
    ENGINE_CRASH = "ENGINE_CRASH"
    INVALID_ACTION = "INVALID_ACTION"
    STALE_REQUEST = "STALE_REQUEST"
    ASSET = "ASSET"
    FIXTURE = "FIXTURE"
    INTERNAL = "INTERNAL"


class ProcessProtocolError(ValueError):
    def __init__(
        self,
        code: ProcessErrorCode,
        message: str,
        *,
        request_id: int | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.request_id = request_id
        super().__init__(message)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


@dataclass(frozen=True, slots=True)
class ProcessRequest:
    message_type: str
    request_id: int
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class HealthResponse:
    request_id: int
    process_state: ProcessState
    adapter_revision: str
    devilutionx_revision: str
    build_fingerprint: str
    observation_version: str
    action_version: str
    supported_task_versions: tuple[str, ...]
    supported_features: tuple[str, ...]
    pid: int
    protocol_version: str = PROCESS_PROTOCOL_VERSION

    def validate_compatibility(self, task_id: str) -> None:
        if self.protocol_version != PROCESS_PROTOCOL_VERSION:
            raise ProcessProtocolError(
                ProcessErrorCode.PROCESS_VERSION_MISMATCH,
                "worker process protocol version is incompatible",
                request_id=self.request_id,
            )
        if self.process_state is not ProcessState.READY:
            raise ProcessProtocolError(
                ProcessErrorCode.INVALID_STATE,
                "worker must be READY before Reset",
                request_id=self.request_id,
            )
        if self.adapter_revision != ADAPTER_REVISION:
            raise ProcessProtocolError(
                ProcessErrorCode.PROCESS_VERSION_MISMATCH,
                "worker adapter revision is incompatible",
                request_id=self.request_id,
            )
        if self.devilutionx_revision != DEVILUTIONX_REVISION:
            raise ProcessProtocolError(
                ProcessErrorCode.PROCESS_VERSION_MISMATCH,
                "worker DevilutionX revision is incompatible",
                request_id=self.request_id,
            )
        if self.build_fingerprint != BUILD_FINGERPRINT:
            raise ProcessProtocolError(
                ProcessErrorCode.PROCESS_VERSION_MISMATCH,
                "worker build fingerprint is incompatible",
                request_id=self.request_id,
            )
        if self.observation_version != OBSERVATION_VERSION:
            raise ProcessProtocolError(
                ProcessErrorCode.PROCESS_VERSION_MISMATCH,
                "worker observation version is incompatible",
                request_id=self.request_id,
            )
        if self.action_version != ACTION_VERSION:
            raise ProcessProtocolError(
                ProcessErrorCode.PROCESS_VERSION_MISMATCH,
                "worker action version is incompatible",
                request_id=self.request_id,
            )
        if self.supported_task_versions != SUPPORTED_TASK_VERSIONS:
            raise ProcessProtocolError(
                ProcessErrorCode.PROCESS_VERSION_MISMATCH,
                "worker task contract is incompatible",
                request_id=self.request_id,
            )
        if self.supported_features != SUPPORTED_FEATURES:
            raise ProcessProtocolError(
                ProcessErrorCode.PROCESS_VERSION_MISMATCH,
                "worker feature contract is incompatible",
                request_id=self.request_id,
            )
        if task_id not in self.supported_task_versions:
            raise ProcessProtocolError(
                ProcessErrorCode.INVALID_FIELD,
                f"worker does not support task {task_id!r}",
                request_id=self.request_id,
            )


@dataclass(frozen=True, slots=True)
class ResetResponse:
    request_id: int
    episode_id: str
    observation: Observation
    candidate_set_sha256: str
    process_state: ProcessState
    protocol_version: str = PROCESS_PROTOCOL_VERSION

    def validate(self) -> None:
        _validate_response_identity(self.protocol_version, self.request_id)
        if self.process_state is not ProcessState.EPISODE_ACTIVE:
            raise ProcessProtocolError(
                ProcessErrorCode.INVALID_STATE,
                "Reset response must activate an episode",
                request_id=self.request_id,
            )
        self.observation.validate()
        if self.observation.step_id != 0:
            raise ProcessProtocolError(
                ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE,
                "Reset response observation must have step_id=0",
                request_id=self.request_id,
            )
        if self.observation.episode_id != self.episode_id:
            raise ProcessProtocolError(
                ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE,
                "Reset response episode_id does not match observation",
                request_id=self.request_id,
            )
        _validate_digest(self.candidate_set_sha256, "candidate_set_sha256", self.request_id)


@dataclass(frozen=True, slots=True)
class PersistentStepResponse:
    request_id: int
    episode_id: str
    previous_step_id: int
    applied_action: ActionCandidate
    previous_candidate_set_sha256: str
    observation: Observation
    candidate_set_sha256: str
    process_state: ProcessState
    protocol_version: str = PROCESS_PROTOCOL_VERSION

    def validate(self) -> None:
        _validate_response_identity(self.protocol_version, self.request_id)
        if self.process_state is not ProcessState.EPISODE_ACTIVE:
            raise ProcessProtocolError(
                ProcessErrorCode.INVALID_STATE,
                "Step response must keep the episode active",
                request_id=self.request_id,
            )
        self.applied_action.validate()
        self.observation.validate()
        if self.episode_id != self.observation.episode_id:
            raise ProcessProtocolError(
                ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE,
                "Step response episode_id does not match observation",
                request_id=self.request_id,
            )
        if self.observation.step_id != self.previous_step_id + 1:
            raise ProcessProtocolError(
                ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE,
                "Step response must increment step_id exactly once",
                request_id=self.request_id,
            )
        _validate_digest(
            self.previous_candidate_set_sha256,
            "previous_candidate_set_sha256",
            self.request_id,
        )
        _validate_digest(self.candidate_set_sha256, "candidate_set_sha256", self.request_id)


@dataclass(frozen=True, slots=True)
class ErrorResponse:
    request_id: int | None
    process_state: ProcessState
    error_code: ProcessErrorCode
    error_message: str
    protocol_version: str = PROCESS_PROTOCOL_VERSION


ProcessResponse = HealthResponse | ResetResponse | PersistentStepResponse | ErrorResponse


_REQUEST_FIELDS: dict[str, frozenset[str]] = {
    "health_request": frozenset({"type", "protocol_version", "request_id"}),
    "reset_request": frozenset({"type", "protocol_version", "request_id", "seed", "task_id"}),
    "step_request": frozenset(
        {
            "type",
            "protocol_version",
            "request_id",
            "episode_id",
            "expected_step_id",
            "candidate_id",
            "candidate_set_sha256",
        }
    ),
}


def parse_process_request(payload: dict[str, Any]) -> ProcessRequest:
    if not isinstance(payload, dict):
        raise ProcessProtocolError(ProcessErrorCode.MALFORMED_JSON, "request must be a JSON object")
    message_type = payload.get("type")
    if not isinstance(message_type, str) or message_type not in _REQUEST_FIELDS:
        raise ProcessProtocolError(
            ProcessErrorCode.UNKNOWN_MESSAGE_TYPE,
            "request type is unsupported",
        )
    expected_fields = _REQUEST_FIELDS[message_type]
    unknown_fields = set(payload) - expected_fields
    if unknown_fields:
        raise ProcessProtocolError(
            ProcessErrorCode.UNKNOWN_FIELD,
            f"unknown request field: {sorted(unknown_fields)[0]}",
        )
    missing_fields = expected_fields - set(payload)
    if missing_fields:
        raise ProcessProtocolError(
            ProcessErrorCode.MISSING_FIELD,
            f"missing request field: {sorted(missing_fields)[0]}",
        )
    version = payload["protocol_version"]
    if version != PROCESS_PROTOCOL_VERSION:
        raise ProcessProtocolError(
            ProcessErrorCode.PROTOCOL_VERSION_MISMATCH,
            f"unsupported process protocol version: {version!r}",
        )
    request_id = _unsigned(payload["request_id"], "request_id", MAX_UINT64)
    if message_type == "reset_request":
        _unsigned(payload["seed"], "seed", MAX_UINT32)
        _non_empty_string(payload["task_id"], "task_id")
    elif message_type == "step_request":
        _non_empty_string(payload["episode_id"], "episode_id")
        _unsigned(payload["expected_step_id"], "expected_step_id", MAX_UINT64)
        _unsigned(payload["candidate_id"], "candidate_id", MAX_UINT32)
        _digest(payload["candidate_set_sha256"], "candidate_set_sha256")
    return ProcessRequest(message_type, request_id, dict(payload))


def make_health_request(request_id: int) -> dict[str, Any]:
    return {
        "type": "health_request",
        "protocol_version": PROCESS_PROTOCOL_VERSION,
        "request_id": request_id,
    }


def make_reset_request(request_id: int, *, seed: int, task_id: str) -> dict[str, Any]:
    return {
        "type": "reset_request",
        "protocol_version": PROCESS_PROTOCOL_VERSION,
        "request_id": request_id,
        "seed": seed,
        "task_id": task_id,
    }


def make_step_request(
    request_id: int,
    *,
    episode_id: str,
    expected_step_id: int,
    candidate_id: int,
    candidate_set_sha256: str,
) -> dict[str, Any]:
    return {
        "type": "step_request",
        "protocol_version": PROCESS_PROTOCOL_VERSION,
        "request_id": request_id,
        "episode_id": episode_id,
        "expected_step_id": expected_step_id,
        "candidate_id": candidate_id,
        "candidate_set_sha256": candidate_set_sha256,
    }


def parse_process_response(payload: dict[str, Any]) -> ProcessResponse:
    if not isinstance(payload, dict):
        raise ProcessProtocolError(
            ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE,
            "process response must be a JSON object",
        )
    message_type = payload.get("type")
    if message_type == "error_response":
        return _parse_error_response(payload)
    if message_type == "health_response":
        expected = {
            "type",
            "protocol_version",
            "request_id",
            "process_state",
            "adapter_revision",
            "devilutionx_revision",
            "build_fingerprint",
            "observation_version",
            "action_version",
            "supported_task_versions",
            "supported_features",
            "pid",
        }
        _require_response_fields(payload, expected)
        health_response = HealthResponse(
            request_id=_response_uint(payload["request_id"], "request_id"),
            process_state=_response_state(payload["process_state"]),
            adapter_revision=_response_string(payload["adapter_revision"], "adapter_revision"),
            devilutionx_revision=_response_string(
                payload["devilutionx_revision"], "devilutionx_revision"
            ),
            build_fingerprint=_response_string(payload["build_fingerprint"], "build_fingerprint"),
            observation_version=_response_string(
                payload["observation_version"], "observation_version"
            ),
            action_version=_response_string(payload["action_version"], "action_version"),
            supported_task_versions=_response_strings(
                payload["supported_task_versions"], "supported_task_versions"
            ),
            supported_features=_response_strings(
                payload["supported_features"], "supported_features"
            ),
            pid=_response_uint(payload["pid"], "pid"),
        )
        return health_response
    if message_type == "reset_response":
        expected = {
            "type",
            "protocol_version",
            "request_id",
            "process_state",
            "episode_id",
            "observation",
            "candidate_set_sha256",
        }
        _require_response_fields(payload, expected)
        observation = _response_observation(payload["observation"])
        reset_response = ResetResponse(
            request_id=_response_uint(payload["request_id"], "request_id"),
            episode_id=_response_string(payload["episode_id"], "episode_id"),
            observation=observation,
            candidate_set_sha256=_response_string(
                payload["candidate_set_sha256"], "candidate_set_sha256"
            ),
            process_state=_response_state(payload["process_state"]),
        )
        reset_response.validate()
        return reset_response
    if message_type == "step_response":
        expected = {
            "type",
            "protocol_version",
            "request_id",
            "process_state",
            "episode_id",
            "previous_step_id",
            "applied_action",
            "previous_candidate_set_sha256",
            "observation",
            "candidate_set_sha256",
        }
        _require_response_fields(payload, expected)
        step_response = PersistentStepResponse(
            request_id=_response_uint(payload["request_id"], "request_id"),
            episode_id=_response_string(payload["episode_id"], "episode_id"),
            previous_step_id=_response_uint(payload["previous_step_id"], "previous_step_id"),
            applied_action=_response_action(payload["applied_action"]),
            previous_candidate_set_sha256=_response_string(
                payload["previous_candidate_set_sha256"], "previous_candidate_set_sha256"
            ),
            observation=_response_observation(payload["observation"]),
            candidate_set_sha256=_response_string(
                payload["candidate_set_sha256"], "candidate_set_sha256"
            ),
            process_state=_response_state(payload["process_state"]),
        )
        step_response.validate()
        return step_response
    raise ProcessProtocolError(
        ProcessErrorCode.UNKNOWN_MESSAGE_TYPE,
        "unsupported process response type",
    )


def _parse_error_response(payload: dict[str, Any]) -> ErrorResponse:
    expected = {
        "type",
        "protocol_version",
        "request_id",
        "process_state",
        "error_code",
        "error_message",
    }
    _require_response_fields(payload, expected)
    request_id = payload["request_id"]
    if request_id is not None:
        request_id = _response_uint(request_id, "request_id")
    code_value = _response_string(payload["error_code"], "error_code")
    try:
        code = ProcessErrorCode(code_value)
    except ValueError as error:
        raise ProcessProtocolError(
            ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE,
            "unsupported process error code",
        ) from error
    return ErrorResponse(
        request_id=request_id,
        process_state=_response_state(payload["process_state"]),
        error_code=code,
        error_message=_response_string(payload["error_message"], "error_message"),
    )


def _require_response_fields(payload: dict[str, Any], expected: set[str]) -> None:
    unknown = set(payload) - expected
    if unknown:
        raise ProcessProtocolError(
            ProcessErrorCode.UNKNOWN_FIELD,
            f"unknown process response field: {sorted(unknown)[0]}",
        )
    missing = expected - set(payload)
    if missing:
        raise ProcessProtocolError(
            ProcessErrorCode.MISSING_FIELD,
            f"missing process response field: {sorted(missing)[0]}",
        )
    if payload["protocol_version"] != PROCESS_PROTOCOL_VERSION:
        raise ProcessProtocolError(
            ProcessErrorCode.PROCESS_VERSION_MISMATCH,
            "process response version is incompatible",
        )


def _response_state(value: Any) -> ProcessState:
    try:
        return ProcessState(value)
    except ValueError as error:
        raise ProcessProtocolError(
            ProcessErrorCode.INVALID_FIELD, "invalid process state"
        ) from error


def _response_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ProcessProtocolError(
            ProcessErrorCode.INVALID_FIELD, f"{field} must be a non-empty string"
        )
    return value


def _response_uint(value: Any, field: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > MAX_UINT64
    ):
        raise ProcessProtocolError(ProcessErrorCode.INVALID_FIELD, f"{field} must be unsigned")
    return value


def _response_strings(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ProcessProtocolError(ProcessErrorCode.INVALID_FIELD, f"{field} must be a string list")
    return tuple(value)


def _response_observation(value: Any) -> Observation:
    if not isinstance(value, dict):
        raise ProcessProtocolError(
            ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE, "observation must be an object"
        )
    try:
        return Observation.from_dict(value)
    except (KeyError, TypeError, ValueError) as error:
        raise ProcessProtocolError(
            ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE, str(error)
        ) from error


def _response_action(value: Any) -> ActionCandidate:
    if not isinstance(value, dict):
        raise ProcessProtocolError(
            ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE, "applied_action must be an object"
        )
    try:
        return ActionCandidate.from_dict(value)
    except (KeyError, TypeError, ValueError) as error:
        raise ProcessProtocolError(
            ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE, str(error)
        ) from error


def _validate_response_identity(protocol_version: str, request_id: int) -> None:
    if protocol_version != PROCESS_PROTOCOL_VERSION or request_id < 0:
        raise ProcessProtocolError(
            ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE,
            "invalid process response identity",
            request_id=request_id,
        )


def _validate_digest(value: str, field: str, request_id: int) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ProcessProtocolError(
            ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE,
            f"{field} must be lowercase SHA-256",
            request_id=request_id,
        )


def _unsigned(value: Any, field: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > maximum:
        raise ProcessProtocolError(
            ProcessErrorCode.INVALID_FIELD, f"{field} must be an unsigned integer"
        )
    return value


def _non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ProcessProtocolError(
            ProcessErrorCode.INVALID_FIELD, f"{field} must be a non-empty string"
        )
    return value


def _digest(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ProcessProtocolError(
            ProcessErrorCode.INVALID_FIELD, f"{field} must be a SHA-256 digest"
        )
    return value


class RequestCache:
    """Bounded exactly-once cache for already completed process requests."""

    def __init__(self, *, max_entries: int = MAX_REQUEST_CACHE_ENTRIES) -> None:
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        self.max_entries = max_entries
        self._entries: OrderedDict[int, tuple[bytes, bytes]] = OrderedDict()
        self._highest_request_id = -1

    def replay_or_raise(self, request_id: int, fingerprint: bytes) -> bytes | None:
        entry = self._entries.get(request_id)
        if entry is not None:
            cached_fingerprint, response = entry
            if cached_fingerprint != fingerprint:
                raise ProcessProtocolError(
                    ProcessErrorCode.REQUEST_ID_REUSE,
                    "request_id was already used with a different payload",
                    request_id=request_id,
                )
            return response
        if request_id <= self._highest_request_id:
            raise ProcessProtocolError(
                ProcessErrorCode.REQUEST_ID_EXPIRED,
                "request_id is older than the bounded request cache",
                request_id=request_id,
            )
        return None

    def remember(self, request_id: int, fingerprint: bytes, response: bytes) -> None:
        existing = self._entries.get(request_id)
        if existing is not None:
            if existing[0] != fingerprint:
                raise ProcessProtocolError(
                    ProcessErrorCode.REQUEST_ID_REUSE,
                    "request_id was already used with a different payload",
                    request_id=request_id,
                )
            return
        if request_id <= self._highest_request_id:
            raise ProcessProtocolError(
                ProcessErrorCode.REQUEST_ID_EXPIRED,
                "request_id must increase monotonically after cache eviction",
                request_id=request_id,
            )
        self._highest_request_id = request_id
        self._entries[request_id] = (fingerprint, response)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)


class ProcessLifecycle:
    def __init__(self) -> None:
        self.state = ProcessState.READY
        self.episode_id: str | None = None
        self.step_id = 0
        self.candidate_set_sha256: str | None = None

    def begin_episode(self, episode_id: str, candidate_set_sha256: str) -> None:
        if self.state is not ProcessState.READY:
            raise ProcessProtocolError(
                ProcessErrorCode.INVALID_STATE, "worker already has an episode"
            )
        if not episode_id:
            raise ValueError("episode_id must not be empty")
        self.state = ProcessState.EPISODE_ACTIVE
        self.episode_id = episode_id
        self.step_id = 0
        self.candidate_set_sha256 = candidate_set_sha256

    def validate_step(
        self, episode_id: str, expected_step_id: int, candidate_set_sha256: str
    ) -> None:
        if self.state is ProcessState.FAULTED:
            raise ProcessProtocolError(ProcessErrorCode.ENGINE_FAULTED, "worker is faulted")
        if self.state is not ProcessState.EPISODE_ACTIVE:
            raise ProcessProtocolError(
                ProcessErrorCode.INVALID_STATE, "worker has no active episode"
            )
        if episode_id != self.episode_id:
            raise ProcessProtocolError(ProcessErrorCode.STALE_EPISODE, "episode_id is stale")
        if expected_step_id != self.step_id:
            raise ProcessProtocolError(ProcessErrorCode.STALE_STEP, "expected_step_id is stale")
        if candidate_set_sha256 != self.candidate_set_sha256:
            raise ProcessProtocolError(
                ProcessErrorCode.STATE_MISMATCH, "candidate-set identity differs"
            )

    def complete_step(self, episode_id: str, next_step_id: int, candidate_set_sha256: str) -> None:
        if self.state is not ProcessState.EPISODE_ACTIVE or episode_id != self.episode_id:
            raise ProcessProtocolError(
                ProcessErrorCode.INVALID_STATE, "cannot complete inactive episode"
            )
        if next_step_id != self.step_id + 1:
            raise ProcessProtocolError(
                ProcessErrorCode.INVALID_STATE, "step_id must increment exactly once"
            )
        self.step_id = next_step_id
        self.candidate_set_sha256 = candidate_set_sha256

    def fault(self) -> None:
        self.state = ProcessState.FAULTED
