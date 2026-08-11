from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dxai.contracts.actions import ActionKind


@dataclass(frozen=True, slots=True)
class TaskSpec:
    task_id: str
    stage: str
    description: str
    max_decisions: int
    allowed_action_kinds: tuple[ActionKind, ...]
    success_condition: str
    failure_conditions: tuple[str, ...]
    reward_version: str
    train_seed_range: tuple[int, int]
    validation_seeds: tuple[int, ...]
    test_seeds: tuple[int, ...]
    privileged_state_allowed: bool = False

    def validate(self) -> None:
        required_text = (
            self.task_id,
            self.stage,
            self.description,
            self.success_condition,
            self.reward_version,
        )
        if any(not value for value in required_text) or self.max_decisions <= 0:
            raise ValueError("task identifiers and positive max_decisions are required")
        if not self.allowed_action_kinds:
            raise ValueError("a task must allow at least one action kind")
        if len(set(self.allowed_action_kinds)) != len(self.allowed_action_kinds):
            raise ValueError("allowed_action_kinds must be unique")
        lo, hi = self.train_seed_range
        if lo < 0 or hi < lo:
            raise ValueError("invalid train seed range")
        if not self.validation_seeds or not self.test_seeds:
            raise ValueError("validation and test seed sets must be non-empty")
        if len(set(self.validation_seeds)) != len(self.validation_seeds):
            raise ValueError("validation seeds must be unique")
        if len(set(self.test_seeds)) != len(self.test_seeds):
            raise ValueError("test seeds must be unique")
        if min(*self.validation_seeds, *self.test_seeds) < 0:
            raise ValueError("validation and test seeds must be non-negative")
        train = set(range(lo, hi + 1))
        if train.intersection(self.validation_seeds) or train.intersection(self.test_seeds):
            raise ValueError("train seeds must not overlap validation or test seeds")
        if set(self.validation_seeds).intersection(self.test_seeds):
            raise ValueError("validation and test seeds must not overlap")

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "stage": self.stage,
            "description": self.description,
            "max_decisions": self.max_decisions,
            "allowed_action_kinds": [item.value for item in self.allowed_action_kinds],
            "success_condition": self.success_condition,
            "failure_conditions": list(self.failure_conditions),
            "reward_version": self.reward_version,
            "train_seed_range": list(self.train_seed_range),
            "validation_seeds": list(self.validation_seeds),
            "test_seeds": list(self.test_seeds),
            "privileged_state_allowed": self.privileged_state_allowed,
        }
