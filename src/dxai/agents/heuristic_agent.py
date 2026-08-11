from __future__ import annotations

import random

from dxai.agents.base import Agent
from dxai.contracts.actions import ActionCandidate, ActionKind
from dxai.contracts.common import Vec2
from dxai.contracts.observations import EntityKind, Observation


class HeuristicAgent(Agent):
    """Stateful deterministic baseline for the mock contract environment."""

    name = "heuristic"

    def __init__(self) -> None:
        self._rng = random.Random()
        self._visited: set[Vec2] = set()

    def reset(self, seed: int) -> None:
        self._rng.seed(seed)
        self._visited = set()

    def act(self, observation: Observation) -> int:
        self._visited.add(observation.player.position)
        by_kind: dict[ActionKind, list[ActionCandidate]] = {}
        for action in observation.legal_actions:
            by_kind.setdefault(action.kind, []).append(action)

        if ActionKind.ATTACK_ENTITY in by_kind:
            return by_kind[ActionKind.ATTACK_ENTITY][0].candidate_id
        if (
            observation.player.hp <= observation.player.hp_max // 2
            and ActionKind.USE_BELT_SLOT in by_kind
        ):
            return by_kind[ActionKind.USE_BELT_SLOT][0].candidate_id
        if ActionKind.PICK_UP_ITEM in by_kind:
            return by_kind[ActionKind.PICK_UP_ITEM][0].candidate_id

        monsters = [entity for entity in observation.entities if entity.kind is EntityKind.MONSTER]
        moves = by_kind.get(ActionKind.MOVE_TO_TILE, [])
        if monsters and moves:
            target = monsters[0].position
            return min(
                moves,
                key=lambda action: _required_tile(action).manhattan(target),
            ).candidate_id

        unvisited = [
            action for action in moves if _required_tile(action) not in self._visited
        ]
        if unvisited:
            # Stable tie-breaking remains seeded so multiple routes are exercised.
            return self._rng.choice(unvisited).candidate_id
        if moves:
            return self._rng.choice(moves).candidate_id
        return observation.legal_actions[0].candidate_id


def _required_tile(action: ActionCandidate) -> Vec2:
    if action.target_tile is None:
        raise ValueError("expected a tile-target action")
    return action.target_tile
