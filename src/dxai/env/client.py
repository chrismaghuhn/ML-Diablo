from __future__ import annotations

from dxai.contracts.observations import Observation
from dxai.contracts.results import StepResult
from dxai.env.base import Environment


class DevilutionXClient(Environment):
    """Contract boundary for the future process-isolated engine bridge.

    The real implementation must speak the versioned protocol in ``protocol/``.
    Keeping this boundary explicit prevents mock behavior from being mistaken for
    a working DevilutionX integration.
    """

    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint

    def reset(self, *, seed: int, task_id: str) -> Observation:
        raise NotImplementedError(
            "The real DevilutionX bridge is an M0/M1 integration deliverable; "
            "see docs/04_DEVILUTIONX_INTEGRATION.md"
        )

    def step(self, candidate_id: int) -> StepResult:
        raise NotImplementedError("real engine bridge not implemented")

    def close(self) -> None:
        return None
