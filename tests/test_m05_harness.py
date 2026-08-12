from __future__ import annotations

import json
from pathlib import Path

from dxai.env.replay import ReplayDivergence
from dxai.env.vector import VectorEnvironmentError
from dxai.protocol.lifecycle import ProcessErrorCode, ProcessProtocolError
from scripts.m05_acceptance import (
    ExternalInputs,
    _is_known_structured_failure,
    build_pending_report,
    seed_schedule,
    write_run_report,
)


def test_external_inputs_report_all_missing_names_without_inventing_paths() -> None:
    inputs = ExternalInputs.from_mapping({})

    assert inputs.missing_names == (
        "DXAI_M04_PROBE",
        "DXAI_DIABLO_DATA",
        "DXAI_DEVILUTIONX_CORE_ASSETS",
        "DXAI_DEVILUTIONX_RUNTIME",
    )
    report = build_pending_report(inputs)
    assert report["status"] == "PENDING_EXTERNAL_INPUTS"
    assert report["missing_inputs"] == list(inputs.missing_names)
    assert "path" not in json.dumps(report).lower()


def test_seed_schedule_is_deterministic() -> None:
    assert seed_schedule(start=10, count=4) == (10, 11, 12, 13)


def test_write_run_report_publishes_machine_readable_files(tmp_path: Path) -> None:
    output = tmp_path / "m05-run"

    write_run_report(
        output,
        {"schema_version": "dxai.m05.report.v1", "status": "PENDING_EXTERNAL_INPUTS"},
        {"replay": {"recorded": 0}},
    )

    assert json.loads((output / "manifest.json").read_text(encoding="utf-8"))["status"] == (
        "PENDING_EXTERNAL_INPUTS"
    )
    assert json.loads((output / "metrics.json").read_text(encoding="utf-8"))["replay"][
        "recorded"
    ] == 0


def test_m05_documentation_publishes_real_gate_boundary() -> None:
    root = Path(__file__).parents[1]
    runbook = root / "docs/runbooks/M05_REPLAY_SOAK_THROUGHPUT.md"
    backlog = (root / "docs/24_IMPLEMENTATION_BACKLOG.md").read_text(encoding="utf-8")

    assert runbook.is_file()
    text = runbook.read_text(encoding="utf-8")
    assert "dxai.engine_replay.v1" in text
    assert "PENDING_EXTERNAL_INPUTS" in text
    assert "real acceptance pending" in text
    assert "32-step real-asset gate remains open" not in backlog
    assert "Warm reset, rewards, terminal/truncation flags" in backlog


def test_harness_only_classifies_known_structured_failures() -> None:
    protocol_error = ProcessProtocolError(ProcessErrorCode.PROCESS_TIMEOUT, "timeout")
    replay_error = ReplayDivergence(
        step_id=0,
        component="observation",
        expected="a",
        actual="b",
    )
    wrapped_protocol_error = VectorEnvironmentError(1, protocol_error)

    assert _is_known_structured_failure(protocol_error) is True
    assert _is_known_structured_failure(replay_error) is True
    assert _is_known_structured_failure(wrapped_protocol_error) is True
    assert _is_known_structured_failure(RuntimeError("infrastructure")) is False


def test_harness_does_not_classify_unknown_vector_failures() -> None:
    assert _is_known_structured_failure(
        VectorEnvironmentError(0, RuntimeError("worker fixture failed"))
    ) is False
