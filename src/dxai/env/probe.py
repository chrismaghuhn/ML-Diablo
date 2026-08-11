from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from dxai.contracts.observations import Observation


class ProbeErrorCode(StrEnum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    UPSTREAM_COMMIT_MISMATCH = "UPSTREAM_COMMIT_MISMATCH"
    ASSET_DATA_UNAVAILABLE = "ASSET_DATA_UNAVAILABLE"
    ENGINE_INITIALIZATION_FAILED = "ENGINE_INITIALIZATION_FAILED"
    OBSERVATION_CONTRACT_FAILED = "OBSERVATION_CONTRACT_FAILED"
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
        raise ProbeError(
            ProbeErrorCode.OBSERVATION_CONTRACT_FAILED,
            str(error),
        ) from error


@dataclass(frozen=True, slots=True)
class ObservationProbe:
    executable: Path
    assets_path: Path
    core_assets_path: Path
    engine_runtime_path: Path | None = None
    runtime_root: Path | None = None
    timeout_seconds: float = 60.0

    def read(self, *, seed: int, task_id: str) -> Observation:
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
        return parse_probe_observation(result.stdout)
