from __future__ import annotations

import os
import queue
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from dxai.contracts.observations import Observation
from dxai.env.base import Environment
from dxai.env.legal import candidate_set_sha256
from dxai.protocol.framing import MAX_PROCESS_FRAME_BYTES, encode_process_line, parse_process_line
from dxai.protocol.lifecycle import (
    MAX_UINT32,
    MAX_UINT64,
    ErrorResponse,
    HealthResponse,
    PersistentStepResponse,
    ProcessErrorCode,
    ProcessProtocolError,
    ProcessState,
    ResetResponse,
    make_health_request,
    make_reset_request,
    make_step_request,
    parse_process_request,
    parse_process_response,
)


class _WorkerHandle(Protocol):
    pid: int

    def request(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def close(self) -> None: ...


class _WorkerProcess:
    """Synchronous request facade over one persistent native worker."""

    def __init__(
        self,
        command: Sequence[str],
        environment: Mapping[str, str] | None,
        timeout_seconds: float,
        max_frame_bytes: int,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._max_frame_bytes = max_frame_bytes
        try:
            self._process = subprocess.Popen(
                list(command),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path(__file__).resolve().parents[3],
                env=None if environment is None else dict(environment),
                bufsize=0,
            )
        except OSError as error:
            raise ProcessProtocolError(ProcessErrorCode.PROCESS_EXITED, str(error)) from error
        assert self._process.stdin is not None
        assert self._process.stdout is not None
        assert self._process.stderr is not None
        self.pid = self._process.pid
        self._stdout_queue: queue.Queue[bytes | None] = queue.Queue()
        self._stderr_tail = bytearray()
        self._stderr_lock = threading.Lock()
        self._closed = False
        self._unusable = False
        self._stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()

    @property
    def unusable(self) -> bool:
        return self._unusable

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._closed or self._unusable:
            raise ProcessProtocolError(ProcessErrorCode.PROCESS_EXITED, "worker is not usable")
        try:
            parse_process_request(payload)
            frame = encode_process_line(payload, max_frame_bytes=self._max_frame_bytes)
        except ProcessProtocolError:
            raise
        except (TypeError, ValueError) as error:
            raise ProcessProtocolError(ProcessErrorCode.INVALID_FIELD, str(error)) from error
        try:
            assert self._process.stdin is not None
            self._process.stdin.write(frame)
            self._process.stdin.flush()
        except (BrokenPipeError, OSError) as error:
            self._mark_unusable()
            raise ProcessProtocolError(
                ProcessErrorCode.PROCESS_EXITED, "worker stdin is closed"
            ) from error

        try:
            line = self._stdout_queue.get(timeout=self._timeout_seconds)
        except queue.Empty as error:
            self._mark_unusable()
            raise ProcessProtocolError(
                ProcessErrorCode.PROCESS_TIMEOUT, "worker request timed out"
            ) from error
        if line is None:
            self._mark_unusable()
            raise ProcessProtocolError(
                ProcessErrorCode.PROCESS_EXITED, "worker exited before responding"
            )
        try:
            return parse_process_line(line, max_frame_bytes=self._max_frame_bytes)
        except ValueError as error:
            self._mark_unusable()
            raise ProcessProtocolError(
                ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE, str(error)
            ) from error

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._unusable = True
        process = self._process
        if process.stdin is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
        try:
            process.wait(timeout=self._timeout_seconds)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=self._timeout_seconds)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        self._stdout_thread.join(timeout=self._timeout_seconds)
        self._stderr_thread.join(timeout=self._timeout_seconds)

    def _mark_unusable(self) -> None:
        self._unusable = True
        self.close()

    def _read_stdout(self) -> None:
        assert self._process.stdout is not None
        try:
            for line in iter(self._process.stdout.readline, b""):
                self._stdout_queue.put(line)
        finally:
            self._stdout_queue.put(None)

    def _read_stderr(self) -> None:
        assert self._process.stderr is not None
        for line in iter(self._process.stderr.readline, b""):
            with self._stderr_lock:
                self._stderr_tail.extend(line)
                del self._stderr_tail[:-65536]


WorkerFactory = Callable[[Sequence[str], Mapping[str, str] | None, float, int], _WorkerHandle]


class DevilutionXEnvironment:
    """M0.4 cold-reset manager for one persistent native episode per worker."""

    def __init__(
        self,
        *,
        executable: Path,
        assets_path: Path,
        core_assets_path: Path,
        engine_runtime_path: Path | None = None,
        runtime_root: Path | None = None,
        timeout_seconds: float = 60.0,
        worker_factory: WorkerFactory | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.executable = Path(executable)
        self.assets_path = Path(assets_path)
        self.core_assets_path = Path(core_assets_path)
        self.engine_runtime_path = (
            None if engine_runtime_path is None else Path(engine_runtime_path)
        )
        self.runtime_root = None if runtime_root is None else Path(runtime_root)
        self.timeout_seconds = timeout_seconds
        self._worker_factory = worker_factory or _WorkerProcess
        self._worker: _WorkerHandle | None = None
        self._observation: Observation | None = None
        self._candidate_set_sha256: str | None = None
        self._task_id: str | None = None
        self._seed: int | None = None
        self._next_request_id = 1
        self._worker_counter = 0
        self._health: HealthResponse | None = None
        self._last_worker_startup_ns: int | None = None

    @property
    def observation(self) -> Observation | None:
        return self._observation

    @property
    def health(self) -> HealthResponse | None:
        return self._health

    @property
    def last_worker_startup_ns(self) -> int | None:
        return self._last_worker_startup_ns

    @property
    def worker_pid(self) -> int | None:
        return None if self._worker is None else self._worker.pid

    @property
    def candidate_set_sha256(self) -> str | None:
        return self._candidate_set_sha256

    def reset(self, *, seed: int, task_id: str) -> Observation:
        _validate_seed(seed)
        if not task_id:
            raise ValueError("task_id is required")
        self.close()
        worker = self._start_worker()
        self._worker = worker
        try:
            health_value = self._request(make_health_request(self._next_id()))
            if not isinstance(health_value, HealthResponse):
                raise ProcessProtocolError(
                    ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE,
                    "Health request did not return HealthResponse",
                )
            health_value.validate_compatibility(task_id)
            self._health = health_value
            reset_value = self._request(
                make_reset_request(self._next_id(), seed=seed, task_id=task_id)
            )
            if not isinstance(reset_value, ResetResponse):
                raise ProcessProtocolError(
                    ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE,
                    "Reset request did not return ResetResponse",
                )
            expected_hash = candidate_set_sha256(reset_value.observation.legal_actions)
            if reset_value.candidate_set_sha256 != expected_hash:
                raise ProcessProtocolError(
                    ProcessErrorCode.STATE_MISMATCH,
                    "Reset response candidate-set identity does not match observation",
                )
            if reset_value.observation.task_id != task_id or reset_value.observation.seed != seed:
                raise ProcessProtocolError(
                    ProcessErrorCode.STATE_MISMATCH,
                    "Reset response task or seed does not match request",
                )
            self._observation = reset_value.observation
            self._candidate_set_sha256 = reset_value.candidate_set_sha256
            self._task_id = task_id
            self._seed = seed
            return reset_value.observation
        except BaseException:
            self._discard_worker()
            raise

    def step(self, candidate_id: int) -> PersistentStepResponse:
        if self._worker is None or self._observation is None or self._candidate_set_sha256 is None:
            raise ProcessProtocolError(
                ProcessErrorCode.INVALID_STATE, "worker is not usable; call reset first"
            )
        if isinstance(candidate_id, bool) or not isinstance(candidate_id, int) or candidate_id < 0:
            raise ProcessProtocolError(
                ProcessErrorCode.INVALID_CANDIDATE, "candidate_id must be non-negative"
            )
        try:
            action = self._observation.action_by_id(candidate_id)
        except KeyError as error:
            raise ProcessProtocolError(
                ProcessErrorCode.INVALID_CANDIDATE,
                f"candidate {candidate_id} is not legal for the current observation",
            ) from error
        response = self._request(
            make_step_request(
                self._next_id(),
                episode_id=self._observation.episode_id,
                expected_step_id=self._observation.step_id,
                candidate_id=action.candidate_id,
                candidate_set_sha256=self._candidate_set_sha256,
            )
        )
        if not isinstance(response, PersistentStepResponse):
            raise ProcessProtocolError(
                ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE,
                "Step request did not return StepResponse",
            )
        if response.episode_id != self._observation.episode_id:
            raise ProcessProtocolError(
                ProcessErrorCode.STATE_MISMATCH, "Step response changed episode_id"
            )
        if response.previous_step_id != self._observation.step_id:
            raise ProcessProtocolError(
                ProcessErrorCode.STATE_MISMATCH, "Step response changed previous step_id"
            )
        if response.previous_candidate_set_sha256 != self._candidate_set_sha256:
            raise ProcessProtocolError(
                ProcessErrorCode.STATE_MISMATCH, "Step response changed candidate-set identity"
            )
        if response.applied_action != action:
            raise ProcessProtocolError(
                ProcessErrorCode.STATE_MISMATCH, "Step response changed applied action"
            )
        if response.observation.task_id != self._task_id or response.observation.seed != self._seed:
            raise ProcessProtocolError(
                ProcessErrorCode.STATE_MISMATCH,
                "Step response changed task or seed",
            )
        expected_hash = candidate_set_sha256(response.observation.legal_actions)
        if response.candidate_set_sha256 != expected_hash:
            raise ProcessProtocolError(
                ProcessErrorCode.STATE_MISMATCH,
                "Step response candidate-set identity does not match observation",
            )
        self._observation = response.observation
        self._candidate_set_sha256 = response.candidate_set_sha256
        return response

    def health_check(self) -> HealthResponse:
        if self._worker is None:
            raise ProcessProtocolError(ProcessErrorCode.INVALID_STATE, "worker is not usable")
        health_value = self._request(make_health_request(self._next_id()))
        if not isinstance(health_value, HealthResponse):
            raise ProcessProtocolError(
                ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE,
                "Health request did not return HealthResponse",
            )
        health_value.validate_identity()
        if health_value.process_state is ProcessState.FAULTED:
            raise ProcessProtocolError(
                ProcessErrorCode.ENGINE_FAULTED,
                "worker health reports a faulted process",
                request_id=health_value.request_id,
            )
        self._health = health_value
        return health_value

    def close(self) -> None:
        self._discard_worker()
        self._health = None

    def __enter__(self) -> DevilutionXEnvironment:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def _next_id(self) -> int:
        request_id = self._next_request_id
        if request_id > MAX_UINT64:
            raise ProcessProtocolError(ProcessErrorCode.INVALID_FIELD, "request ID exhausted")
        self._next_request_id += 1
        return request_id

    def _start_worker(self) -> _WorkerHandle:
        self._last_worker_startup_ns = None
        if not self.executable.is_file():
            raise ProcessProtocolError(
                ProcessErrorCode.PROCESS_EXITED, "worker executable does not exist"
            )
        if not self.assets_path.is_dir() or not self.core_assets_path.is_dir():
            raise ProcessProtocolError(
                ProcessErrorCode.ASSET, "worker asset directory is unavailable"
            )
        if self.engine_runtime_path is not None:
            if not self.engine_runtime_path.is_dir():
                raise ProcessProtocolError(
                    ProcessErrorCode.ENGINE_FAULT, "engine runtime directory is unavailable"
                )
            if not (self.engine_runtime_path / "libdevilutionx_so.dll").is_file():
                raise ProcessProtocolError(
                    ProcessErrorCode.ENGINE_FAULT, "engine runtime library is unavailable"
                )
        runtime_root = self._new_runtime_root()
        command = [
            str(self.executable),
            "--assets",
            str(self.assets_path),
            "--core-assets",
            str(self.core_assets_path),
            "--runtime-root",
            str(runtime_root),
            "--env-stdio",
        ]
        environment: dict[str, str] | None = None
        if self.engine_runtime_path is not None:
            environment = os.environ.copy()
            environment["PATH"] = os.pathsep.join(
                (str(self.engine_runtime_path), environment.get("PATH", ""))
            )
        try:
            startup_started = time.perf_counter_ns()
            worker = self._worker_factory(
                command,
                environment,
                self.timeout_seconds,
                MAX_PROCESS_FRAME_BYTES,
            )
            self._last_worker_startup_ns = time.perf_counter_ns() - startup_started
            return worker
        except ProcessProtocolError:
            raise
        except OSError as error:
            raise ProcessProtocolError(ProcessErrorCode.PROCESS_EXITED, str(error)) from error

    def _new_runtime_root(self) -> Path:
        if self.runtime_root is None:
            return Path(tempfile.mkdtemp(prefix="dxai-m04-worker-"))
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self._worker_counter += 1
        return Path(
            tempfile.mkdtemp(
                prefix=f"worker-{self._worker_counter}-",
                dir=str(self.runtime_root),
            )
        )

    def _request(
        self, payload: dict[str, Any]
    ) -> HealthResponse | ResetResponse | PersistentStepResponse:
        if self._worker is None:
            raise ProcessProtocolError(ProcessErrorCode.INVALID_STATE, "worker is not usable")
        try:
            process_request = parse_process_request(payload)
            raw_response = self._worker.request(payload)
            response = parse_process_response(raw_response)
        except ProcessProtocolError as error:
            if error.code in {
                ProcessErrorCode.PROCESS_EXITED,
                ProcessErrorCode.PROCESS_TIMEOUT,
                ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE,
                ProcessErrorCode.PROCESS_VERSION_MISMATCH,
                ProcessErrorCode.ENGINE_FAULT,
                ProcessErrorCode.ENGINE_FAULTED,
            }:
                self._discard_worker()
            raise
        if isinstance(response, ErrorResponse):
            if (
                response.request_id is not None
                and response.request_id != process_request.request_id
            ):
                self._discard_worker()
                raise ProcessProtocolError(
                    ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE,
                    "error response request_id does not match request",
                )
            if response.process_state is ProcessState.FAULTED or response.error_code in {
                ProcessErrorCode.ENGINE_FAULT,
                ProcessErrorCode.ENGINE_FAULTED,
                ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE,
                ProcessErrorCode.ASSET_DATA_UNAVAILABLE,
                ProcessErrorCode.ENGINE_INITIALIZATION_FAILED,
                ProcessErrorCode.OBSERVATION_CONTRACT_FAILED,
                ProcessErrorCode.ACTION_RESOLUTION_FAILED,
                ProcessErrorCode.INTERNAL,
            }:
                self._discard_worker()
            raise ProcessProtocolError(
                response.error_code,
                response.error_message,
                request_id=response.request_id,
            )
        if response.request_id != process_request.request_id:
            self._discard_worker()
            raise ProcessProtocolError(
                ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE,
                "response request_id does not match request",
            )
        return response

    def _discard_worker(self) -> None:
        worker = self._worker
        self._worker = None
        self._observation = None
        self._candidate_set_sha256 = None
        self._task_id = None
        self._seed = None
        if worker is not None:
            worker.close()


def _validate_seed(seed: int) -> None:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0 or seed > MAX_UINT32:
        raise ValueError("seed must fit in uint32_t")


class DevilutionXClient(Environment):
    """Compatibility placeholder for the older endpoint-based environment API."""

    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint

    def reset(self, *, seed: int, task_id: str) -> Observation:
        raise NotImplementedError(
            "Use DevilutionXEnvironment for the M0.4 process lifecycle; "
            "endpoint transport is not implemented"
        )

    def step(self, candidate_id: int) -> Any:
        raise NotImplementedError("Use DevilutionXEnvironment for the M0.4 process lifecycle")

    def close(self) -> None:
        return None
