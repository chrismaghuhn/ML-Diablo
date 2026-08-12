from __future__ import annotations

import os
from pathlib import Path

import pytest

from dxai.diagnostics.metrics import (
    FailureCounter,
    ResourceSample,
    classify_failure,
    latency_summary_ns,
    process_alive,
    runtime_directory_metrics,
    sample_resources,
)
from dxai.protocol.lifecycle import ProcessErrorCode, ProcessProtocolError


def test_latency_summary_reports_median_p95_p99_after_warmup() -> None:
    summary = latency_summary_ns([10, 20, 30, 40, 50], warmup_count=1)

    assert summary["sample_count"] == 4
    assert summary["warmup_count"] == 1
    assert summary["median_ns"] == 35.0
    assert summary["p95_ns"] == pytest.approx(48.5)
    assert summary["p99_ns"] == pytest.approx(49.7)


def test_latency_summary_rejects_empty_or_non_finite_samples() -> None:
    with pytest.raises(ValueError, match="sample"):
        latency_summary_ns([], warmup_count=0)
    with pytest.raises(ValueError, match="finite"):
        latency_summary_ns([1.0, float("nan")], warmup_count=0)


def test_failure_counter_classifies_known_and_unexpected_errors() -> None:
    class RecordedDivergence:
        code = ProcessErrorCode.REPLAY_DIVERGENCE

    counter = FailureCounter()
    counter.record(ProcessProtocolError(ProcessErrorCode.NO_SUPPORTED_CANDIDATES, "fixture"))
    counter.record(RecordedDivergence())
    counter.record(RuntimeError("unexpected"))

    assert counter.to_dict() == {
        "NO_SUPPORTED_CANDIDATES": 1,
        "REPLAY_DIVERGENCE": 1,
        "UNEXPECTED_EXCEPTION": 1,
    }
    assert classify_failure(ProcessErrorCode.REPLAY_DIVERGENCE) == "REPLAY_DIVERGENCE"


def test_runtime_directory_metrics_counts_regular_files_only(tmp_path: Path) -> None:
    (tmp_path / "a.bin").write_bytes(b"123")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "b.bin").write_bytes(b"4567")

    result = runtime_directory_metrics(tmp_path)

    assert result == {"file_count": 2, "total_bytes": 7}


def test_sample_resources_is_serializable_and_uses_current_process() -> None:
    sample = sample_resources(os.getpid(), None)

    assert isinstance(sample, ResourceSample)
    assert sample.pid == os.getpid()
    assert sample.timestamp_ns > 0
    assert isinstance(sample.to_dict(), dict)


def test_process_alive_reports_current_and_absent_processes() -> None:
    assert process_alive(os.getpid()) is True
    assert process_alive(2**31 - 1) is False
