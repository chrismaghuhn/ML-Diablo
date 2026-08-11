from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from dxai.agents.base import Agent
from dxai.contracts.observations import Observation
from dxai.data.trajectory import TransitionRecord, read_episode
from dxai.env.mock import DeterministicCombatEnv
from dxai.evaluation.runner import run_episode


def test_episode_manifest_matches_records(recorded_episode) -> None:
    directory, manifest, records, metrics = recorded_episode
    assert manifest.step_count == len(records) == metrics.steps
    assert manifest.outcome == "SUCCESS"
    assert manifest.data_source == "SCRIPTED"
    assert records[-1].terminated
    assert (directory / manifest.trajectory_file).exists()


def test_transition_round_trip(recorded_episode) -> None:
    _, _, records, _ = recorded_episode
    record = records[0]
    assert TransitionRecord.from_dict(record.to_dict()) == record


def test_tampering_is_detected(recorded_episode) -> None:
    directory, manifest, _, _ = recorded_episode
    trajectory = directory / manifest.trajectory_file
    trajectory.write_text(trajectory.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum"):
        read_episode(directory)


def test_manifest_step_count_mismatch_is_detected(recorded_episode) -> None:
    directory, _, _, _ = recorded_episode
    manifest_path = directory / "manifest.json"
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    value["step_count"] += 1
    manifest_path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="step count"):
        read_episode(directory)


def test_recorder_leaves_no_temporary_file(recorded_episode) -> None:
    directory, _, _, _ = recorded_episode
    assert not list(Path(directory).glob("*.tmp"))


class _CrashingAgent(Agent):
    name = "crashing"

    def reset(self, seed: int) -> None:
        del seed

    def act(self, observation: Observation) -> int:
        del observation
        raise RuntimeError("intentional agent failure")


def test_failed_episode_is_not_published_as_training_data(tmp_path: Path) -> None:
    env = DeterministicCombatEnv()
    try:
        with pytest.raises(RuntimeError, match="intentional"):
            run_episode(
                env,
                _CrashingAgent(),
                seed=33,
                task_id="combat.single_melee.v0",
                record_root=tmp_path,
            )
    finally:
        env.close()
    assert list(tmp_path.iterdir()) == []


def test_transition_requires_exact_candidate_copy(recorded_episode) -> None:
    _, _, records, _ = recorded_episode
    record = records[0]
    tampered = replace(
        record,
        action=replace(record.action, label=record.action.label + " tampered"),
    )
    with pytest.raises(ValueError, match="exactly match"):
        tampered.validate()


def test_manifest_rejects_unsafe_trajectory_path(recorded_episode) -> None:
    directory, _, _, _ = recorded_episode
    manifest_path = directory / "manifest.json"
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    value["trajectory_file"] = "../outside.jsonl"
    manifest_path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="safe file name"):
        read_episode(directory)
