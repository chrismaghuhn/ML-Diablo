from __future__ import annotations

import struct

import pytest

from dxai.protocol.framing import (
    FrameDecoder,
    encode_frame,
    encode_process_line,
    parse_process_line,
)
from dxai.protocol.lifecycle import (
    PROCESS_PROTOCOL_VERSION,
    ProcessErrorCode,
    ProcessProtocolError,
    parse_process_request,
    parse_process_response,
)
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


def test_process_line_is_utf8_json_and_bounded_to_one_megabyte() -> None:
    payload = {
        "type": "health_request",
        "protocol_version": PROCESS_PROTOCOL_VERSION,
        "request_id": 7,
    }
    encoded = encode_process_line(payload)
    assert encoded.endswith(b"\n")
    assert parse_process_line(encoded[:-1]) == payload

    with pytest.raises(ValueError, match="1 MiB"):
        encode_process_line({"value": "x" * (1024 * 1024)})

    with pytest.raises(ValueError, match="UTF-8"):
        parse_process_line(b'{"type":"health_request","value":"\xff"}')

    with pytest.raises(ValueError, match="one JSON object"):
        parse_process_line(b'{"type":"health_request","request_id":1,"request_id":2}')


def test_process_request_rejects_unknown_fields_and_wrong_version() -> None:
    request = {
        "type": "health_request",
        "protocol_version": PROCESS_PROTOCOL_VERSION,
        "request_id": 1,
        "extra": False,
    }
    with pytest.raises(ProcessProtocolError) as unknown:
        parse_process_request(request)
    assert unknown.value.code is ProcessErrorCode.UNKNOWN_FIELD

    request.pop("extra")
    request["protocol_version"] = "dxai.process.v0"
    with pytest.raises(ProcessProtocolError) as version:
        parse_process_request(request)
    assert version.value.code is ProcessErrorCode.PROTOCOL_VERSION_MISMATCH


def test_process_response_rejects_unknown_error_code() -> None:
    with pytest.raises(ProcessProtocolError) as error:
        parse_process_response(
            {
                "type": "error_response",
                "protocol_version": PROCESS_PROTOCOL_VERSION,
                "request_id": 1,
                "process_state": "READY",
                "error_code": "NOT_A_PROCESS_ERROR",
                "error_message": "invalid",
            }
        )
    assert error.value.code is ProcessErrorCode.PROTOCOL_MALFORMED_RESPONSE
