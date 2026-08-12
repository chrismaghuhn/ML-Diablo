from __future__ import annotations

import ctypes
import math
import os
import re
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dxai.protocol.lifecycle import ProcessErrorCode, ProcessProtocolError

UNAVAILABLE = "UNAVAILABLE"
_KNOWN_FAILURE_CODES = frozenset(code.value for code in ProcessErrorCode)


@dataclass(frozen=True, slots=True)
class ResourceSample:
    timestamp_ns: int
    pid: int
    rss_bytes: int | None
    handle_count: int | None
    process_count: int | None
    open_file_descriptors: int | None
    runtime_file_count: int
    runtime_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_ns": self.timestamp_ns,
            "pid": self.pid,
            "rss_bytes": _available(self.rss_bytes),
            "handle_count": _available(self.handle_count),
            "process_count": _available(self.process_count),
            "open_file_descriptors": _available(self.open_file_descriptors),
            "runtime_file_count": self.runtime_file_count,
            "runtime_bytes": self.runtime_bytes,
        }


class FailureCounter:
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def record(self, failure: object) -> None:
        code = classify_failure(failure)
        self._counts[code] = self._counts.get(code, 0) + 1

    def to_dict(self) -> dict[str, int]:
        return dict(sorted(self._counts.items()))


def classify_failure(failure: object) -> str:
    if isinstance(failure, ProcessProtocolError):
        return failure.code.value
    if isinstance(failure, ProcessErrorCode):
        return failure.value
    code = getattr(failure, "code", None)
    if isinstance(code, ProcessErrorCode):
        return code.value
    if isinstance(code, str) and code in _KNOWN_FAILURE_CODES:
        return code
    cause_code = getattr(getattr(failure, "cause", None), "code", None)
    if isinstance(cause_code, ProcessErrorCode):
        return cause_code.value
    if isinstance(cause_code, str) and cause_code in _KNOWN_FAILURE_CODES:
        return cause_code
    if isinstance(failure, str) and failure in _KNOWN_FAILURE_CODES:
        return failure
    return "UNEXPECTED_EXCEPTION"


def latency_summary_ns(
    values: Iterable[int | float], *, warmup_count: int
) -> dict[str, float | int]:
    raw = list(values)
    if warmup_count < 0 or warmup_count >= len(raw):
        raise ValueError("warmup_count must leave at least one sample")
    for value in raw:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("latency samples must be numeric")
        if not math.isfinite(float(value)) or value < 0:
            raise ValueError("latency samples must be finite and non-negative")
    samples = sorted(float(value) for value in raw[warmup_count:])
    return {
        "sample_count": len(samples),
        "warmup_count": warmup_count,
        "median_ns": _quantile(samples, 0.50),
        "p95_ns": _quantile(samples, 0.95),
        "p99_ns": _quantile(samples, 0.99),
    }


def runtime_directory_metrics(root: Path | None) -> dict[str, int]:
    if root is None or not root.exists():
        return {"file_count": 0, "total_bytes": 0}
    file_count = 0
    total_bytes = 0
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            total_bytes += path.stat().st_size
        except OSError:
            continue
        file_count += 1
    return {"file_count": file_count, "total_bytes": total_bytes}


def sample_resources(pid: int, runtime_root: Path | None) -> ResourceSample:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise ValueError("pid must be a positive integer")
    rss_bytes: int | None
    handle_count: int | None
    process_count: int | None
    open_file_descriptors: int | None
    if os.name == "nt":
        rss_bytes, handle_count = _windows_process_metrics(pid)
        process_count = None
        open_file_descriptors = None
    else:
        rss_bytes = _proc_rss_bytes(pid)
        handle_count = None
        process_count = None
        open_file_descriptors = _proc_fd_count(pid)
    runtime = runtime_directory_metrics(runtime_root)
    return ResourceSample(
        timestamp_ns=time.perf_counter_ns(),
        pid=pid,
        rss_bytes=rss_bytes,
        handle_count=handle_count,
        process_count=process_count,
        open_file_descriptors=open_file_descriptors,
        runtime_file_count=runtime["file_count"],
        runtime_bytes=runtime["total_bytes"],
    )


def process_alive(pid: int) -> bool | str:
    """Return whether a known worker PID is still alive after close."""

    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise ValueError("pid must be a positive integer")
    if os.name == "nt":
        return _windows_process_alive(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return UNAVAILABLE
    return True


def _quantile(samples: list[float], probability: float) -> float:
    if not samples:
        raise ValueError("at least one latency sample is required")
    position = (len(samples) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return samples[lower]
    fraction = position - lower
    return samples[lower] + fraction * (samples[upper] - samples[lower])


def _available(value: int | None) -> int | str:
    return UNAVAILABLE if value is None else value


def _proc_rss_bytes(pid: int) -> int | None:
    status_path = Path(f"/proc/{pid}/status")
    try:
        text = status_path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r"^VmRSS:\s+(\d+)\s+kB$", text, flags=re.MULTILINE)
    return None if match is None else int(match.group(1)) * 1024


def _proc_fd_count(pid: int) -> int | None:
    path = Path(f"/proc/{pid}/fd")
    try:
        return sum(1 for item in path.iterdir() if not item.is_symlink())
    except OSError:
        return None


def _windows_process_metrics(pid: int) -> tuple[int | None, int | None]:
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(
        PROCESS_QUERY_INFORMATION | PROCESS_QUERY_LIMITED_INFORMATION,
        False,
        pid,
    )
    if not handle:
        return None, None

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    try:
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        memory_ok = ctypes.windll.psapi.GetProcessMemoryInfo(
            handle,
            ctypes.byref(counters),
            counters.cb,
        )
        rss = int(counters.WorkingSetSize) if memory_ok else None
        handles = ctypes.c_ulong()
        handle_ok = ctypes.windll.kernel32.GetProcessHandleCount(
            handle,
            ctypes.byref(handles),
        )
        return rss, int(handles.value) if handle_ok else None
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def _windows_process_alive(pid: int) -> bool | str:
    SYNCHRONIZE = 0x00100000
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    handle = ctypes.windll.kernel32.OpenProcess(
        SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION,
        False,
        pid,
    )
    if not handle:
        return False
    try:
        exit_code = ctypes.c_ulong()
        if not ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return UNAVAILABLE
        return int(exit_code.value) == STILL_ACTIVE
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)
