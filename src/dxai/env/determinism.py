from __future__ import annotations

import hashlib
from typing import Any

from dxai.contracts.serialization import canonical_json_bytes

_LIFECYCLE_KEYS = frozenset(
    {
        "request_id",
        "pid",
        "process_id",
        "runtime_root",
        "timestamp",
        "timestamps",
        "process_launch",
    }
)
_LIFECYCLE_EPISODE_PLACEHOLDER = "<lifecycle-episode>"


def canonicalize_m04_trace(value: Any) -> Any:
    """Remove only documented lifecycle metadata from a semantic trace."""

    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if key in _LIFECYCLE_KEYS:
                continue
            if key == "episode_id":
                result[key] = _LIFECYCLE_EPISODE_PLACEHOLDER
            else:
                result[key] = canonicalize_m04_trace(item)
        return result
    if isinstance(value, list):
        return [canonicalize_m04_trace(item) for item in value]
    if isinstance(value, tuple):
        return [canonicalize_m04_trace(item) for item in value]
    return value


def canonical_trace_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(canonicalize_m04_trace(value))).hexdigest()
