from __future__ import annotations

import struct

import pytest

from dxai.protocol.framing import FrameDecoder, encode_frame
from dxai.protocol.messages import (
    ACTION_VERSION,
    OBSERVATION_VERSION,
    PROTOCOL_VERSION,
    Handshake,
    ResetRequest,
    StepRequest,
)


def test_messages_validate_and_serialize() -> None:
    handshake = Handshake(
        protocol_version=PROTOCOL_VERSION,
        observation_version=OBSERVATION_VERSION,
        action_version=ACTION_VERSION,
        adapter_revision="adapter-1",
        engine_revision="0738584",
        build_fingerprint="sha256:abc",
        supported_tasks=("combat.single_melee.v0",),
    )
    handshake.validate()
    assert handshake.to_dict()["engine_revision"] == "0738584"
    reset = ResetRequest(request_id=1, seed=42, task_id="combat.single_melee.v0")
    reset.validate()
    step = StepRequest(request_id=2, episode_id="e", expected_step_id=0, candidate_id=1)
    step.validate()


def test_length_prefixed_framing_handles_partial_and_multiple_frames() -> None:
    first = encode_frame({"request_id": 1, "kind": "health"})
    second = encode_frame({"request_id": 2, "kind": "reset"})
    decoder = FrameDecoder()
    assert decoder.feed(first[:3]) == []
    messages = decoder.feed(first[3:] + second)
    assert [item["request_id"] for item in messages] == [1, 2]
    assert decoder.buffered_bytes == 0


def test_oversized_declared_frame_is_rejected() -> None:
    decoder = FrameDecoder(max_frame_bytes=10)
    with pytest.raises(ValueError, match="exceeds"):
        decoder.feed(struct.pack(">I", 11))


def test_framing_rejects_non_standard_nan_constant() -> None:
    body = b'{"value":NaN}'
    decoder = FrameDecoder()
    with pytest.raises(ValueError, match="non-JSON"):
        decoder.feed(struct.pack(">I", len(body)) + body)
