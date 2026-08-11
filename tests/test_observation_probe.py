from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from dxai.env.probe import ObservationProbe, ProbeError, ProbeErrorCode, parse_probe_error


def test_structured_probe_error_round_trip() -> None:
    error = parse_probe_error(
        '{"error_code":"ASSET_DATA_UNAVAILABLE",'
        '"error_message":"required Diablo data is unavailable"}'
    )
    assert error.code is ProbeErrorCode.ASSET_DATA_UNAVAILABLE
    assert str(error) == "ASSET_DATA_UNAVAILABLE: required Diablo data is unavailable"


def test_probe_error_rejects_unstructured_stderr() -> None:
    error = parse_probe_error("fatal process output")
    assert isinstance(error, ProbeError)
    assert error.code is ProbeErrorCode.INTERNAL


def test_probe_requires_existing_engine_runtime_path(tmp_path: Path) -> None:
    executable = tmp_path / "probe.exe"
    executable.touch()
    assets = tmp_path / "diablo"
    assets.mkdir()
    core_assets = tmp_path / "core-assets"
    core_assets.mkdir()
    probe = ObservationProbe(
        executable=executable,
        assets_path=assets,
        core_assets_path=core_assets,
        engine_runtime_path=tmp_path / "missing-runtime",
    )

    with pytest.raises(ProbeError) as raised:
        probe.read(seed=1, task_id="combat.single_melee.v0")

    assert raised.value.code is ProbeErrorCode.ENGINE_INITIALIZATION_FAILED


def test_probe_rejects_seed_outside_engine_range(tmp_path: Path) -> None:
    probe = ObservationProbe(
        executable=tmp_path / "probe.exe",
        assets_path=tmp_path / "diablo",
        core_assets_path=tmp_path / "core-assets",
    )

    with pytest.raises(ProbeError) as raised:
        probe.read(seed=2**32, task_id="combat.single_melee.v0")

    assert raised.value.code is ProbeErrorCode.INVALID_ARGUMENT


def test_probe_requires_engine_runtime_library(tmp_path: Path) -> None:
    executable = tmp_path / "probe.exe"
    executable.touch()
    assets = tmp_path / "diablo"
    assets.mkdir()
    core_assets = tmp_path / "core-assets"
    core_assets.mkdir()
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    probe = ObservationProbe(
        executable=executable,
        assets_path=assets,
        core_assets_path=core_assets,
        engine_runtime_path=runtime,
    )

    with pytest.raises(ProbeError) as raised:
        probe.read(seed=1, task_id="combat.single_melee.v0")

    assert raised.value.code is ProbeErrorCode.ENGINE_INITIALIZATION_FAILED


def test_probe_passes_separate_core_assets_and_runtime_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "probe.exe"
    executable.touch()
    assets = tmp_path / "diablo"
    assets.mkdir()
    core_assets = tmp_path / "core-assets"
    core_assets.mkdir()
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "libdevilutionx_so.dll").touch()
    payload = json.loads(
        (Path(__file__).parents[1] / "schemas/examples/observation.example.json").read_text(
            encoding="utf-8"
        )
    )
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured.update(kwargs)
        return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    observation = ObservationProbe(
        executable=executable,
        assets_path=assets,
        core_assets_path=core_assets,
        engine_runtime_path=runtime,
    ).read(seed=7, task_id="combat.single_melee.v0")

    command = captured["command"]
    assert isinstance(command, list)
    assert "--core-assets" in command
    assert str(core_assets) in command
    environment = captured["env"]
    assert isinstance(environment, dict)
    assert str(runtime) in str(environment["PATH"])
    assert observation.schema_version == "dxai.observation.v1"
