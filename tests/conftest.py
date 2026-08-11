from __future__ import annotations

from pathlib import Path

import pytest

from dxai.agents.heuristic_agent import HeuristicAgent
from dxai.data.trajectory import read_episode
from dxai.env.mock import DeterministicCombatEnv
from dxai.evaluation.runner import run_episode


@pytest.fixture
def recorded_episode(tmp_path: Path):
    env = DeterministicCombatEnv()
    try:
        metrics = run_episode(
            env,
            HeuristicAgent(),
            seed=17,
            task_id="combat.single_melee.v0",
            record_root=tmp_path,
            data_source="SCRIPTED",
        )
    finally:
        env.close()
    directory = next(path for path in tmp_path.iterdir() if path.is_dir())
    manifest, records = read_episode(directory)
    return directory, manifest, records, metrics
