from __future__ import annotations

from dataclasses import replace

import pytest

from dxai.tasks.registry import get_task, list_tasks
from dxai.training.r2d3 import R2D3Config


def test_task_registry_is_sorted_and_valid() -> None:
    tasks = list_tasks()
    assert tasks
    assert [item.task_id for item in tasks] == sorted(item.task_id for item in tasks)
    for task in tasks:
        task.validate()
        assert not set(task.validation_seeds).intersection(task.test_seeds)


def test_get_task() -> None:
    assert get_task("combat.single_melee.v0").stage == "M1"


def test_r2d3_start_config() -> None:
    config = R2D3Config()
    config.validate()
    assert config.learning_length == 40
    epsilons = config.actor_epsilons()
    assert len(epsilons) == config.actor_count
    assert all(0 < value < 1 for value in epsilons)


def test_r2d3_config_rejects_invalid_beta_schedule() -> None:
    with pytest.raises(ValueError, match="beta schedule"):
        replace(
            R2D3Config(),
            importance_beta_start=0.9,
            importance_beta_end=0.4,
        ).validate()
