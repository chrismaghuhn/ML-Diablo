from __future__ import annotations

import math
from dataclasses import dataclass

from dxai.contracts.actions import ActionCandidate, ActionKind
from dxai.contracts.observations import EntityKind, Observation

_CANDIDATE_AUX_DIM = 8


@dataclass(frozen=True, slots=True)
class FeatureSpec:
    version: str = "dxai.features.v1"
    state_dim: int = 16
    candidate_aux_dim: int = _CANDIDATE_AUX_DIM
    candidate_dim: int = len(ActionKind) + 10 + _CANDIDATE_AUX_DIM


def encode_observation(observation: Observation) -> list[float]:
    """Compact reference features; production should use richer object/grid encoders."""
    visible_monsters = [
        item for item in observation.entities if item.kind is EntityKind.MONSTER and item.hostile
    ]
    visible_items = [item for item in observation.entities if item.kind is EntityKind.ITEM]
    distances = [observation.player.position.manhattan(item.position) for item in visible_monsters]
    explored = sum(tile.explored for tile in observation.local_tiles)
    visible = sum(tile.visible for tile in observation.local_tiles)
    walkable = sum(tile.explored and tile.walkable for tile in observation.local_tiles)
    tile_count = max(1, len(observation.local_tiles))
    return [
        observation.player.hp / observation.player.hp_max,
        0.0
        if observation.player.mana_max == 0
        else observation.player.mana / observation.player.mana_max,
        min(observation.player.level / 50.0, 1.0),
        math.log1p(observation.player.experience) / 20.0,
        math.log1p(observation.player.gold) / 15.0,
        min(observation.player.potions / 8.0, 1.0),
        min(observation.player.dungeon_level / 16.0, 1.0),
        min(len(visible_monsters) / 12.0, 1.0),
        min(min(distances, default=32) / 32.0, 1.0),
        min(len(visible_items) / 12.0, 1.0),
        explored / tile_count,
        visible / tile_count,
        walkable / tile_count,
        math.tanh(observation.player.position.x / 32.0),
        math.tanh(observation.player.position.y / 32.0),
        min(len(observation.legal_actions) / 128.0, 1.0),
    ]


def encode_candidate(action: ActionCandidate, observation: Observation) -> list[float]:
    action.validate()
    one_hot = [0.0] * len(ActionKind)
    one_hot[list(ActionKind).index(action.kind)] = 1.0
    target_dx = 0.0
    target_dy = 0.0
    target_distance = 0.0
    if action.target_tile is not None:
        target_dx = math.tanh((action.target_tile.x - observation.player.position.x) / 8.0)
        target_dy = math.tanh((action.target_tile.y - observation.player.position.y) / 8.0)
        target_distance = min(
            observation.player.position.manhattan(action.target_tile) / 32.0,
            1.0,
        )
    elif action.target_entity_id is not None:
        entity = next(
            (item for item in observation.entities if item.entity_id == action.target_entity_id),
            None,
        )
        if entity is not None:
            target_dx = math.tanh((entity.position.x - observation.player.position.x) / 8.0)
            target_dy = math.tanh((entity.position.y - observation.player.position.y) / 8.0)
            target_distance = min(
                observation.player.position.manhattan(entity.position) / 32.0,
                1.0,
            )
    payload = [
        target_dx,
        target_dy,
        target_distance,
        _norm_optional(action.inventory_slot, 40),
        _norm_optional(action.equipment_slot, 8),
        _norm_optional(action.belt_slot, 8),
        _norm_optional(action.spell_id, 256),
        _norm_optional(action.store_item_id, 128),
        _norm_optional(action.stat_id, 8),
        min(len(action.features) / 64.0, 1.0),
    ]
    auxiliary = [math.tanh(value) for value in action.features[:_CANDIDATE_AUX_DIM]]
    auxiliary.extend([0.0] * (_CANDIDATE_AUX_DIM - len(auxiliary)))
    return one_hot + payload + auxiliary


def encode_candidates(observation: Observation) -> list[list[float]]:
    return [encode_candidate(action, observation) for action in observation.legal_actions]


def _norm_optional(value: int | None, denominator: int) -> float:
    return 0.0 if value is None else min((value + 1) / denominator, 1.0)
