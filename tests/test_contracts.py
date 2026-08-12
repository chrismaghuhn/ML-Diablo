from __future__ import annotations

from dataclasses import replace

import pytest

from dxai.contracts.actions import ActionCandidate, ActionKind
from dxai.contracts.common import Vec2
from dxai.contracts.observations import (
    InventoryContainer,
    InventoryItem,
    Observation,
    PlayerState,
    TileCell,
)
from dxai.contracts.results import StepResult
from dxai.contracts.serialization import canonical_json
from dxai.env.legal import (
    assign_candidate_ids,
    candidate_set_sha256,
    canonical_candidate_set_key,
)
from dxai.env.mock import DeterministicCombatEnv


def test_action_round_trip_and_validation() -> None:
    action = ActionCandidate(
        candidate_id=3,
        kind=ActionKind.CAST_SPELL_AT_ENTITY,
        target_entity_id=99,
        spell_id=7,
        label="Firebolt",
        features=(0.2, 0.3),
    )
    assert ActionCandidate.from_dict(action.to_dict()) == action
    with pytest.raises(ValueError, match="requires target_entity_id"):
        ActionCandidate(0, ActionKind.ATTACK_ENTITY).validate()
    with pytest.raises(ValueError, match="forbids payload"):
        ActionCandidate(0, ActionKind.WAIT, target_entity_id=1).validate()
    with pytest.raises(ValueError, match="finite"):
        ActionCandidate(0, ActionKind.WAIT, features=(float("nan"),)).validate()
    ActionCandidate(
        0,
        ActionKind.EQUIP_ITEM,
        inventory_slot=4,
        equipment_slot=1,
    ).validate()


def test_candidate_ids_are_deterministic_and_dense() -> None:
    unordered = [
        ActionCandidate(-1, ActionKind.MOVE_TO_TILE, target_tile=Vec2(3, 2)),
        ActionCandidate(-1, ActionKind.WAIT),
        ActionCandidate(-1, ActionKind.MOVE_TO_TILE, target_tile=Vec2(2, 3)),
    ]
    assigned = assign_candidate_ids(unordered)
    assert [item.candidate_id for item in assigned] == [0, 1, 2]
    assert [item.semantic_key() for item in assigned] == sorted(
        item.semantic_key() for item in unordered
    )


def test_duplicate_semantic_candidates_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate semantic action"):
        assign_candidate_ids(
            [ActionCandidate(-1, ActionKind.WAIT), ActionCandidate(-1, ActionKind.WAIT)]
        )


def test_candidate_set_identity_is_ordered_and_excludes_descriptive_fields() -> None:
    candidates = assign_candidate_ids(
        [
            ActionCandidate(
                -1,
                ActionKind.MOVE_TO_TILE,
                target_tile=Vec2(3, 2),
                label="different label",
                features=(1.0,),
            ),
            ActionCandidate(-1, ActionKind.MOVE_TO_TILE, target_tile=Vec2(2, 3)),
        ]
    )
    expected = (
        "dxai.observation.v1|dxai.action.v1|"
        "candidate_id=0;kind=MOVE_TO_TILE;target_entity_id=null;target_tile=2,3;"
        "inventory_slot=null;equipment_slot=null;belt_slot=null;spell_id=null;"
        "store_item_id=null;stat_id=null||"
        "candidate_id=1;kind=MOVE_TO_TILE;target_entity_id=null;target_tile=3,2;"
        "inventory_slot=null;equipment_slot=null;belt_slot=null;spell_id=null;"
        "store_item_id=null;stat_id=null"
    )
    assert canonical_candidate_set_key(candidates) == expected
    assert candidate_set_sha256(candidates) == candidate_set_sha256(
        [
            ActionCandidate(
                0,
                ActionKind.MOVE_TO_TILE,
                target_tile=Vec2(2, 3),
                label="ignored",
                features=(9.0,),
            ),
            ActionCandidate(1, ActionKind.MOVE_TO_TILE, target_tile=Vec2(3, 2)),
        ]
    )


def test_observation_round_trip() -> None:
    env = DeterministicCombatEnv()
    try:
        observation = env.reset(seed=9, task_id="combat.single_melee.v0")
    finally:
        env.close()
    restored = Observation.from_dict(observation.to_dict())
    assert restored == observation


def test_player_inventory_round_trip_and_visibility_safe_validation() -> None:
    player = PlayerState(
        position=Vec2(4, 5),
        hp=20,
        hp_max=20,
        inventory=(
            InventoryItem(
                container=InventoryContainer.BELT,
                slot=0,
                type_id="HEALING_POTION",
                identified=True,
            ),
            InventoryItem(
                container=InventoryContainer.INVENTORY,
                slot=2,
                type_id="UNIDENTIFIED",
                identified=False,
            ),
        ),
    )
    assert PlayerState.from_dict(player.to_dict()) == player

    with pytest.raises(ValueError, match="inventory slot"):
        PlayerState(
            position=Vec2(0, 0),
            hp=1,
            hp_max=1,
            inventory=(
                InventoryItem(InventoryContainer.BELT, 0, "HEALING_POTION", True),
                InventoryItem(InventoryContainer.BELT, 0, "MANA_POTION", True),
            ),
        ).validate()

    with pytest.raises(ValueError, match="UNIDENTIFIED"):
        InventoryItem(
            container=InventoryContainer.INVENTORY,
            slot=0,
            type_id="SWORD",
            identified=False,
        ).validate()


def test_unexplored_tile_cannot_leak_terrain_or_occupancy() -> None:
    with pytest.raises(ValueError, match="terrain_id=-1"):
        TileCell(
            relative=Vec2(1, 1),
            terrain_id=1,
            walkable=False,
            visible=False,
            explored=False,
        ).validate()
    with pytest.raises(ValueError, match="occupancy"):
        TileCell(
            relative=Vec2(1, 1),
            terrain_id=1,
            walkable=True,
            visible=False,
            explored=True,
            occupied=True,
        ).validate()


def test_candidate_is_bound_to_current_observation() -> None:
    env = DeterministicCombatEnv()
    try:
        observation = env.reset(seed=3, task_id="combat.single_melee.v0")
        with pytest.raises(KeyError):
            observation.action_by_id(999)
        broken = replace(
            observation,
            legal_actions=(replace(observation.legal_actions[0], candidate_id=1),),
        )
        with pytest.raises(ValueError, match="dense"):
            broken.validate()
    finally:
        env.close()


def test_strict_json_and_step_result_reject_non_finite_values() -> None:
    with pytest.raises(ValueError):
        canonical_json({"reward": float("nan")})
    env = DeterministicCombatEnv()
    try:
        observation = env.reset(seed=2, task_id="combat.single_melee.v0")
    finally:
        env.close()
    with pytest.raises(ValueError, match="finite"):
        StepResult(
            observation=observation,
            reward=float("inf"),
            terminated=False,
            truncated=False,
            info={},
        ).validate()
