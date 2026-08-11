from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from dxai.contracts.observations import Observation


@dataclass(frozen=True, slots=True)
class StepResult:
    observation: Observation
    reward: float
    terminated: bool
    truncated: bool
    info: dict[str, Any]

    def validate(self) -> None:
        self.observation.validate()
        if not math.isfinite(self.reward):
            raise ValueError("step reward must be finite")
        if self.terminated and self.truncated:
            raise ValueError("a step cannot be both terminated and truncated")
        if not isinstance(self.info, dict):
            raise ValueError("step info must be a dictionary")
