from __future__ import annotations

from abc import ABC, abstractmethod

from dxai.contracts.observations import Observation
from dxai.contracts.results import StepResult


class Environment(ABC):
    @abstractmethod
    def reset(self, *, seed: int, task_id: str) -> Observation:
        """Start a deterministic episode for the given task and seed."""

    @abstractmethod
    def step(self, candidate_id: int) -> StepResult:
        """Execute one currently legal candidate and advance to the next decision boundary."""

    @abstractmethod
    def close(self) -> None:
        """Release engine resources."""
