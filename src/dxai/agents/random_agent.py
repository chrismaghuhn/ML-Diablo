from __future__ import annotations

import random

from dxai.agents.base import Agent
from dxai.contracts.observations import Observation


class RandomAgent(Agent):
    name = "random"

    def __init__(self) -> None:
        self._rng = random.Random()

    def reset(self, seed: int) -> None:
        self._rng.seed(seed)

    def act(self, observation: Observation) -> int:
        return self._rng.choice(observation.legal_actions).candidate_id
