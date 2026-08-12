from __future__ import annotations

from dataclasses import replace

import pytest

from dxai.contracts.actions import ActionCandidate, ActionKind
from dxai.contracts.common import Vec2
from dxai.contracts.observations import Observation
from dxai.env.observability import validate_observable_move_candidates


def _observation() -> Observation:
    from dxai.env.mock import DeterministicCombatEnv

    env = DeterministicCombatEnv()
    try:
        return env.reset(seed=7, task_id="combat.single_melee.v0")
    finally:
        env.close()


def _open_tiles(observation: Observation, relatives: set[Vec2]) -> Observation:
    return replace(
        observation,
        local_tiles=tuple(
            replace(
                tile,
                terrain_id=1,
                walkable=True,
                visible=True,
                explored=True,
                occupied=False,
            )
            if tile.relative in relatives
            else tile
            for tile in observation.local_tiles
        ),
    )


def test_move_candidate_must_be_explained_by_visible_open_tiles() -> None:
    observation = _observation()
    move = ActionCandidate(
        0,
        ActionKind.MOVE_TO_TILE,
        target_tile=Vec2(
            observation.player.position.x + 1,
            observation.player.position.y,
        ),
    )
    audited = replace(
        _open_tiles(observation, {Vec2(1, 0), Vec2(1, -1), Vec2(1, 1)}),
        legal_actions=(move,),
    )
    validate_observable_move_candidates(audited)

    hidden_target = replace(
        audited,
        local_tiles=tuple(
            replace(tile, visible=False)
            if tile.relative == Vec2(1, 0)
            else tile
            for tile in audited.local_tiles
        ),
    )
    with pytest.raises(ValueError, match="non-visible"):
        validate_observable_move_candidates(hidden_target)


def test_move_candidate_must_not_depend_on_unobserved_cardinal_corner() -> None:
    observation = _observation()
    move = ActionCandidate(
        0,
        ActionKind.MOVE_TO_TILE,
        target_tile=Vec2(
            observation.player.position.x,
            observation.player.position.y - 1,
        ),
    )
    audited = replace(
        _open_tiles(observation, {Vec2(0, -1), Vec2(-1, -1), Vec2(1, -1)}),
        legal_actions=(move,),
    )
    corner_hidden = replace(
        audited,
        local_tiles=tuple(
            replace(tile, visible=False)
            if tile.relative == Vec2(-1, -1)
            else tile
            for tile in audited.local_tiles
        ),
    )
    with pytest.raises(ValueError, match="non-visible"):
        validate_observable_move_candidates(corner_hidden)
