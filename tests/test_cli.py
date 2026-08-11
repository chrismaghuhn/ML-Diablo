from __future__ import annotations

import json
from pathlib import Path

from dxai.cli import main


def test_smoke_cli_writes_summary(tmp_path: Path, capsys) -> None:
    assert main(["smoke", "--episodes", "2", "--output", str(tmp_path)]) == 0
    value = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert value["aggregate"]["episodes"] == 2
    assert value["aggregate"]["success_rate"] == 1.0
    assert "summary=" in capsys.readouterr().out


def test_ml_plan_and_tasks_cli(capsys) -> None:
    assert main(["ml-plan"]) == 0
    output = capsys.readouterr().out
    assert "R2D3-style" in output
    assert "demonstration_ratio" in output
    assert main(["tasks"]) == 0
    assert "combat.single_melee.v0" in capsys.readouterr().out
