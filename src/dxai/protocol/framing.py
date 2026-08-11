from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field
from typing import Any, NoReturn

from dxai.contracts.serialization import canonical_json_bytes

MAX_FRAME_BYTES = 16 * 1024 * 1024
_HEADER = struct.Struct(">I")


def encode_frame(payload: dict[str, Any], *, max_frame_bytes: int = MAX_FRAME_BYTES) -> bytes:
    if max_frame_bytes <= 0:
        raise ValueError("max_frame_bytes must be positive")
    body = canonical_json_bytes(payload)
    if len(body) > max_frame_bytes:
        raise ValueError(f"frame exceeds {max_frame_bytes} bytes")
    return _HEADER.pack(len(body)) + body


def _reject_non_json_number(value: str) -> NoReturn:
    raise ValueError(f"non-JSON numeric constant {value!r} is forbidden")


@dataclass(slots=True)
class FrameDecoder:
    max_frame_bytes: int = MAX_FRAME_BYTES
    _buffer: bytearray = field(default_factory=bytearray, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.max_frame_bytes <= 0:
            raise ValueError("max_frame_bytes must be positive")

    def feed(self, data: bytes) -> list[dict[str, Any]]:
        self._buffer.extend(data)
        messages: list[dict[str, Any]] = []
        while len(self._buffer) >= _HEADER.size:
            (length,) = _HEADER.unpack(self._buffer[: _HEADER.size])
            if length > self.max_frame_bytes:
                self._buffer.clear()
                raise ValueError(f"declared frame exceeds {self.max_frame_bytes} bytes")
            frame_end = _HEADER.size + length
            if len(self._buffer) < frame_end:
                break
            body = bytes(self._buffer[_HEADER.size:frame_end])
            del self._buffer[:frame_end]
            value = json.loads(body, parse_constant=_reject_non_json_number)
            if not isinstance(value, dict):
                raise ValueError("protocol frame must contain a JSON object")
            messages.append(value)
        return messages

    @property
    def buffered_bytes(self) -> int:
        return len(self._buffer)
