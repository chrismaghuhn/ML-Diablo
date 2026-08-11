from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from dxai.contracts.actions import ActionCandidate
from dxai.contracts.common import Vec2


class EntityKind(StrEnum):
    MONSTER = "MONSTER"
    ITEM = "ITEM"
    OBJECT = "OBJECT"
    MISSILE = "MISSILE"
    NPC = "NPC"
    STAIRS = "STAIRS"


class InventoryContainer(StrEnum):
    EQUIPPED = "EQUIPPED"
    INVENTORY = "INVENTORY"
    BELT = "BELT"


@dataclass(frozen=True, slots=True)
class InventoryItem:
    container: InventoryContainer
    slot: int
    type_id: str
    identified: bool
    quantity: int = 1

    def validate(self) -> None:
        if not isinstance(self.container, InventoryContainer):
            raise ValueError("inventory container must be an InventoryContainer")
        if self.slot < 0:
            raise ValueError("inventory slot must be non-negative")
        if not self.type_id:
            raise ValueError("inventory type_id is required")
        if self.identified and self.type_id == "UNIDENTIFIED":
            raise ValueError("identified inventory items cannot use UNIDENTIFIED")
        if not self.identified and self.type_id != "UNIDENTIFIED":
            raise ValueError("unidentified inventory items must use UNIDENTIFIED")
        if self.quantity < 1:
            raise ValueError("inventory quantity must be positive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "container": self.container.value,
            "slot": self.slot,
            "type_id": self.type_id,
            "identified": self.identified,
            "quantity": self.quantity,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> InventoryItem:
        result = cls(
            container=InventoryContainer(value["container"]),
            slot=int(value["slot"]),
            type_id=str(value["type_id"]),
            identified=bool(value["identified"]),
            quantity=int(value.get("quantity", 1)),
        )
        result.validate()
        return result


@dataclass(frozen=True, slots=True)
class PlayerState:
    position: Vec2
    hp: int
    hp_max: int
    mana: int = 0
    mana_max: int = 0
    level: int = 1
    experience: int = 0
    gold: int = 0
    potions: int = 0
    class_id: str = "WARRIOR"
    dungeon_level: int = 1
    attributes: tuple[tuple[str, float], ...] = ()
    inventory: tuple[InventoryItem, ...] = ()

    def validate(self) -> None:
        if self.hp_max <= 0 or not 0 <= self.hp <= self.hp_max:
            raise ValueError("invalid player HP")
        if self.mana_max < 0 or not 0 <= self.mana <= self.mana_max:
            raise ValueError("invalid player mana")
        if self.level <= 0 or self.experience < 0 or self.gold < 0 or self.potions < 0:
            raise ValueError("invalid non-negative player field")
        if self.dungeon_level < 0 or not self.class_id:
            raise ValueError("invalid player class or dungeon level")
        keys = [key for key, _ in self.attributes]
        if len(keys) != len(set(keys)) or any(not key for key in keys):
            raise ValueError("player attribute keys must be non-empty and unique")
        if any(not math.isfinite(value) for _, value in self.attributes):
            raise ValueError("player attributes must be finite")
        inventory_slots = [(item.container, item.slot) for item in self.inventory]
        if len(inventory_slots) != len(set(inventory_slots)):
            raise ValueError("inventory slot entries must be unique")
        for item in self.inventory:
            item.validate()

    def to_dict(self) -> dict[str, Any]:
        return {
            "position": self.position.to_dict(),
            "hp": self.hp,
            "hp_max": self.hp_max,
            "mana": self.mana,
            "mana_max": self.mana_max,
            "level": self.level,
            "experience": self.experience,
            "gold": self.gold,
            "potions": self.potions,
            "class_id": self.class_id,
            "dungeon_level": self.dungeon_level,
            "attributes": {key: value for key, value in self.attributes},
            "inventory": [item.to_dict() for item in self.inventory],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> PlayerState:
        attributes = value.get("attributes", {})
        result = cls(
            position=Vec2.from_dict(value["position"]),
            hp=int(value["hp"]),
            hp_max=int(value["hp_max"]),
            mana=int(value.get("mana", 0)),
            mana_max=int(value.get("mana_max", 0)),
            level=int(value.get("level", 1)),
            experience=int(value.get("experience", 0)),
            gold=int(value.get("gold", 0)),
            potions=int(value.get("potions", 0)),
            class_id=str(value.get("class_id", "WARRIOR")),
            dungeon_level=int(value.get("dungeon_level", 1)),
            attributes=tuple(sorted((str(k), float(v)) for k, v in attributes.items())),
            inventory=tuple(
                InventoryItem.from_dict(item) for item in value.get("inventory", [])
            ),
        )
        result.validate()
        return result


@dataclass(frozen=True, slots=True)
class EntityState:
    entity_id: int
    kind: EntityKind
    position: Vec2
    type_id: str
    hp: int | None = None
    hp_max: int | None = None
    hostile: bool = False
    visible: bool = True
    attributes: tuple[tuple[str, float], ...] = ()

    def validate(self) -> None:
        if self.entity_id < 0 or not self.type_id:
            raise ValueError("entity_id must be non-negative and type_id is required")
        if (self.hp is None) != (self.hp_max is None):
            raise ValueError("hp and hp_max must either both be present or both be absent")
        if self.hp is not None and self.hp_max is not None:
            if self.hp_max <= 0 or not 0 <= self.hp <= self.hp_max:
                raise ValueError("invalid entity HP")
        keys = [key for key, _ in self.attributes]
        if len(keys) != len(set(keys)) or any(not key for key in keys):
            raise ValueError("entity attribute keys must be non-empty and unique")
        if any(not math.isfinite(value) for _, value in self.attributes):
            raise ValueError("entity attributes must be finite")

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "kind": self.kind.value,
            "position": self.position.to_dict(),
            "type_id": self.type_id,
            "hp": self.hp,
            "hp_max": self.hp_max,
            "hostile": self.hostile,
            "visible": self.visible,
            "attributes": {key: value for key, value in self.attributes},
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> EntityState:
        attributes = value.get("attributes", {})
        result = cls(
            entity_id=int(value["entity_id"]),
            kind=EntityKind(value["kind"]),
            position=Vec2.from_dict(value["position"]),
            type_id=str(value["type_id"]),
            hp=None if value.get("hp") is None else int(value["hp"]),
            hp_max=None if value.get("hp_max") is None else int(value["hp_max"]),
            hostile=bool(value.get("hostile", False)),
            visible=bool(value.get("visible", True)),
            attributes=tuple(sorted((str(k), float(v)) for k, v in attributes.items())),
        )
        result.validate()
        return result


@dataclass(frozen=True, slots=True)
class TileCell:
    relative: Vec2
    terrain_id: int
    walkable: bool
    visible: bool
    explored: bool
    occupied: bool = False
    hazard: float = 0.0

    def validate(self) -> None:
        if not self.explored and self.terrain_id != -1:
            raise ValueError("unexplored tiles must use terrain_id=-1")
        if self.explored and self.terrain_id < 0:
            raise ValueError("explored tiles must use a non-negative terrain_id")
        if not self.explored and self.walkable:
            raise ValueError("unexplored tiles must not reveal walkability")
        if not self.visible and self.occupied:
            raise ValueError("non-visible tiles must not reveal current occupancy")
        if self.hazard < 0 or not math.isfinite(self.hazard):
            raise ValueError("hazard must be finite and non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "relative": self.relative.to_dict(),
            "terrain_id": self.terrain_id,
            "walkable": self.walkable,
            "visible": self.visible,
            "explored": self.explored,
            "occupied": self.occupied,
            "hazard": self.hazard,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> TileCell:
        result = cls(
            relative=Vec2.from_dict(value["relative"]),
            terrain_id=int(value["terrain_id"]),
            walkable=bool(value["walkable"]),
            visible=bool(value["visible"]),
            explored=bool(value["explored"]),
            occupied=bool(value.get("occupied", False)),
            hazard=float(value.get("hazard", 0.0)),
        )
        result.validate()
        return result


@dataclass(frozen=True, slots=True)
class Observation:
    schema_version: str
    episode_id: str
    task_id: str
    seed: int
    step_id: int
    engine_tick: int
    decision_reason: str
    player: PlayerState
    local_tiles: tuple[TileCell, ...]
    entities: tuple[EntityState, ...]
    legal_actions: tuple[ActionCandidate, ...]
    recent_events: tuple[str, ...] = ()

    def validate(self) -> None:
        if self.schema_version != "dxai.observation.v1":
            raise ValueError("unsupported observation schema version")
        if not self.episode_id or not self.task_id or not self.decision_reason:
            raise ValueError("episode_id, task_id and decision_reason are required")
        if self.seed < 0 or self.step_id < 0 or self.engine_tick < 0:
            raise ValueError("seed, step_id and engine_tick must be non-negative")
        self.player.validate()
        ids = [action.candidate_id for action in self.legal_actions]
        if not ids:
            raise ValueError("an observation must expose at least one legal action")
        if ids != list(range(len(ids))):
            raise ValueError("candidate IDs must be dense and ordered from zero")
        semantic_keys = [action.semantic_key() for action in self.legal_actions]
        if len(semantic_keys) != len(set(semantic_keys)):
            raise ValueError("semantic action candidates must be unique")
        for action in self.legal_actions:
            action.validate()
        entity_ids = [entity.entity_id for entity in self.entities]
        if len(entity_ids) != len(set(entity_ids)):
            raise ValueError("entity IDs must be unique in an observation")
        for entity in self.entities:
            entity.validate()
            if not entity.visible:
                raise ValueError("entities in v1 observations must be currently visible")
        tile_positions = [tile.relative for tile in self.local_tiles]
        if len(tile_positions) != len(set(tile_positions)):
            raise ValueError("local tile coordinates must be unique")
        for tile in self.local_tiles:
            tile.validate()

    def action_by_id(self, candidate_id: int) -> ActionCandidate:
        if 0 <= candidate_id < len(self.legal_actions):
            action = self.legal_actions[candidate_id]
            if action.candidate_id == candidate_id:
                return action
        raise KeyError(f"candidate {candidate_id} is not legal for step {self.step_id}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "episode_id": self.episode_id,
            "task_id": self.task_id,
            "seed": self.seed,
            "step_id": self.step_id,
            "engine_tick": self.engine_tick,
            "decision_reason": self.decision_reason,
            "player": self.player.to_dict(),
            "local_tiles": [tile.to_dict() for tile in self.local_tiles],
            "entities": [entity.to_dict() for entity in self.entities],
            "legal_actions": [action.to_dict() for action in self.legal_actions],
            "recent_events": list(self.recent_events),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Observation:
        result = cls(
            schema_version=str(value["schema_version"]),
            episode_id=str(value["episode_id"]),
            task_id=str(value["task_id"]),
            seed=int(value["seed"]),
            step_id=int(value["step_id"]),
            engine_tick=int(value["engine_tick"]),
            decision_reason=str(value["decision_reason"]),
            player=PlayerState.from_dict(value["player"]),
            local_tiles=tuple(TileCell.from_dict(item) for item in value["local_tiles"]),
            entities=tuple(EntityState.from_dict(item) for item in value["entities"]),
            legal_actions=tuple(
                ActionCandidate.from_dict(item) for item in value["legal_actions"]
            ),
            recent_events=tuple(str(item) for item in value.get("recent_events", [])),
        )
        result.validate()
        return result
