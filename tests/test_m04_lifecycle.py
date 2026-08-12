from __future__ import annotations

import pytest

from dxai.protocol.lifecycle import (
    ProcessErrorCode,
    ProcessLifecycle,
    ProcessProtocolError,
    RequestCache,
)


def test_request_cache_replays_exact_duplicate_and_rejects_changed_payload() -> None:
    cache = RequestCache(max_entries=2)
    cache.remember(10, b"payload-a", b"response-a")

    assert cache.replay_or_raise(10, b"payload-a") == b"response-a"
    with pytest.raises(ProcessProtocolError) as changed:
        cache.replay_or_raise(10, b"payload-b")
    assert changed.value.code is ProcessErrorCode.REQUEST_ID_REUSE


def test_request_cache_rejects_evicted_ids_instead_of_reexecuting_them() -> None:
    cache = RequestCache(max_entries=2)
    cache.remember(1, b"one", b"response-one")
    cache.remember(2, b"two", b"response-two")
    cache.remember(3, b"three", b"response-three")

    with pytest.raises(ProcessProtocolError) as expired:
        cache.replay_or_raise(1, b"one")
    assert expired.value.code is ProcessErrorCode.REQUEST_ID_EXPIRED


def test_lifecycle_requires_reset_before_step_and_advances_once() -> None:
    lifecycle = ProcessLifecycle()
    with pytest.raises(ProcessProtocolError) as before_reset:
        lifecycle.validate_step("episode-a", 0, "hash-a")
    assert before_reset.value.code is ProcessErrorCode.INVALID_STATE

    lifecycle.begin_episode("episode-a", "hash-a")
    lifecycle.validate_step("episode-a", 0, "hash-a")
    lifecycle.complete_step("episode-a", 1, "hash-b")
    assert lifecycle.step_id == 1

    with pytest.raises(ProcessProtocolError) as stale:
        lifecycle.validate_step("episode-a", 0, "hash-b")
    assert stale.value.code is ProcessErrorCode.STALE_STEP


def test_lifecycle_fault_blocks_future_steps() -> None:
    lifecycle = ProcessLifecycle()
    lifecycle.begin_episode("episode-a", "hash-a")
    lifecycle.fault()

    with pytest.raises(ProcessProtocolError) as faulted:
        lifecycle.validate_step("episode-a", 0, "hash-a")
    assert faulted.value.code is ProcessErrorCode.ENGINE_FAULTED
