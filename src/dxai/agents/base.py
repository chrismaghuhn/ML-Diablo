from __future__ import annotations

from abc import ABC, abstractmethod

from dxai.contracts.observations import Observation


class Agent(ABC):
    name: str

    @abstractmethod
    def reset(self, seed: int) -> None:
        """Reset all episode-local memory."""

    @abstractmethod
    def act(self, observation: Observation) -> int:
        """Return one currently legal candidate ID."""
