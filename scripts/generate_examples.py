#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from dxai.agents.heuristic_agent import HeuristicAgent
from dxai.contracts.serialization import canonical_json
from dxai.data.trajectory import read_episode
from dxai.env.mock import DeterministicCombatEnv
from dxai.evaluation.runner import run_episode
from dxai.training.checkpoint import CheckpointManifest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "schemas" / "examples"


def write(name: str, value: object) -> None:
    (OUTPUT / name).write_text(canonical_json(value) + "\n", encoding="utf-8")


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dxai-examples-") as temporary:
        env = DeterministicCombatEnv()
        try:
            run_episode(
                env,
                HeuristicAgent(),
                seed=7,
                task_id="combat.single_melee.v0",
                record_root=Path(temporary),
                data_source="SCRIPTED",
            )
        finally:
            env.close()
        directory = next(path for path in Path(temporary).iterdir() if path.is_dir())
        manifest, records = read_episode(directory)
    first = records[0]
    write("action.example.json", first.action.to_dict())
    write("observation.example.json", first.observation.to_dict())
    write("transition.example.json", first.to_dict())
    write("episode_manifest.example.json", manifest.to_dict())
    checkpoint = CheckpointManifest(
        schema_version="dxai.checkpoint.v1",
        run_id="example-run",
        learner_step=1000,
        model_class="CandidateQNetwork",
        observation_version="dxai.observation.v1",
        action_version="dxai.action.v1",
        task_ids=("combat.single_melee.v0",),
        upstream_revision="07385842840437cc9a785b195f5b40b121eaeb1c",
        config_sha256="a" * 64,
        weights_sha256="b" * 64,
        metrics={"validation_success_rate": 0.75},
    )
    write("checkpoint.example.json", checkpoint.to_dict())
    print(f"wrote examples to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
