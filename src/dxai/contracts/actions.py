from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from dxai.contracts.common import Vec2


class ActionKind(StrEnum):
    WAIT = "WAIT"
    MOVE_TO_TILE = "MOVE_TO_TILE"
    ATTACK_ENTITY = "ATTACK_ENTITY"
    CAST_SPELL_AT_ENTITY = "CAST_SPELL_AT_ENTITY"
    CAST_SPELL_AT_TILE = "CAST_SPELL_AT_TILE"
    USE_BELT_SLOT = "USE_BELT_SLOT"
    PICK_UP_ITEM = "PICK_UP_ITEM"
    OPERATE_OBJECT = "OPERATE_OBJECT"
    EQUIP_ITEM = "EQUIP_ITEM"
    UNEQUIP_ITEM = "UNEQUIP_ITEM"
    DROP_ITEM = "DROP_ITEM"
    BUY_ITEM = "BUY_ITEM"
    SELL_ITEM = "SELL_ITEM"
    REPAIR_ITEM = "REPAIR_ITEM"
    ALLOCATE_STAT = "ALLOCATE_STAT"
    TAKE_STAIRS = "TAKE_STAIRS"
    RETURN_TO_TOWN = "RETURN_TO_TOWN"


_PAYLOAD_FIELDS = (
    "target_entity_id",
    "target_tile",
    "inventory_slot",
    "equipment_slot",
    "belt_slot",
    "spell_id",
    "store_item_id",
    "stat_id",
)
_PAYLOAD_CONTRACT: dict[ActionKind, tuple[frozenset[str], frozenset[str]]] = {
    ActionKind.WAIT: (frozenset(), frozenset()),
    ActionKind.MOVE_TO_TILE: (
        frozenset({"target_tile"}),
        frozenset({"target_tile"}),
    ),
    ActionKind.ATTACK_ENTITY: (
        frozenset({"target_entity_id"}),
        frozenset({"target_entity_id"}),
    ),
    ActionKind.CAST_SPELL_AT_ENTITY: (
        frozenset({"target_entity_id", "spell_id"}),
        frozenset({"target_entity_id", "spell_id"}),
    ),
    ActionKind.CAST_SPELL_AT_TILE: (
        frozenset({"target_tile", "spell_id"}),
        frozenset({"target_tile", "spell_id"}),
    ),
    ActionKind.USE_BELT_SLOT: (
        frozenset({"belt_slot"}),
        frozenset({"belt_slot"}),
    ),
    ActionKind.PICK_UP_ITEM: (
        frozenset({"target_entity_id"}),
        frozenset({"target_entity_id"}),
    ),
    ActionKind.OPERATE_OBJECT: (
        frozenset({"target_entity_id"}),
        frozenset({"target_entity_id"}),
    ),
    ActionKind.EQUIP_ITEM: (
        frozenset({"inventory_slot"}),
        frozenset({"inventory_slot", "equipment_slot"}),
    ),
    ActionKind.UNEQUIP_ITEM: (
        frozenset({"equipment_slot"}),
        frozenset({"equipment_slot"}),
    ),
    ActionKind.DROP_ITEM: (
        frozenset({"inventory_slot"}),
        frozenset({"inventory_slot"}),
    ),
    ActionKind.BUY_ITEM: (
        frozenset({"store_item_id"}),
        frozenset({"store_item_id"}),
    ),
    ActionKind.SELL_ITEM: (
        frozenset({"inventory_slot"}),
        frozenset({"inventory_slot"}),
    ),
    ActionKind.REPAIR_ITEM: (
        frozenset({"inventory_slot"}),
        frozenset({"inventory_slot"}),
    ),
    ActionKind.ALLOCATE_STAT: (
        frozenset({"stat_id"}),
        frozenset({"stat_id"}),
    ),
    ActionKind.TAKE_STAIRS: (
        frozenset({"target_entity_id"}),
        frozenset({"target_entity_id"}),
    ),
    ActionKind.RETURN_TO_TOWN: (frozenset(), frozenset()),
}
_MAX_CANDIDATE_FEATURES = 64


@dataclass(frozen=True, slots=True)
class ActionCandidate:
    """One legal semantic choice at a single decision boundary.

    ``candidate_id`` is observation-local. The semantic payload is also stored so a
    recorded trajectory remains meaningful after candidates are re-numbered.
    """

    candidate_id: int
    kind: ActionKind
    target_entity_id: int | None = None
    target_tile: Vec2 | None = None
    inventory_slot: int | None = None
    equipment_slot: int | None = None
    belt_slot: int | None = None
    spell_id: int | None = None
    store_item_id: int | None = None
    stat_id: int | None = None
    label: str = ""
    features: tuple[float, ...] = ()

    def validate(self) -> None:
        if self.candidate_id < 0:
            raise ValueError("candidate_id must be non-negative")
        if not isinstance(self.kind, ActionKind):
            raise ValueError("kind must be an ActionKind")

        payload = {name: getattr(self, name) for name in _PAYLOAD_FIELDS}
        required, allowed = _PAYLOAD_CONTRACT[self.kind]
        missing = sorted(name for name in required if payload[name] is None)
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"{self.kind} requires {joined}")
        unexpected = sorted(
            name for name, value in payload.items() if value is not None and name not in allowed
        )
        if unexpected:
            joined = ", ".join(unexpected)
            raise ValueError(f"{self.kind} forbids payload field(s): {joined}")

        for name in (
            "target_entity_id",
            "inventory_slot",
            "equipment_slot",
            "belt_slot",
            "spell_id",
            "store_item_id",
            "stat_id",
        ):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} must be non-negative")

        if len(self.features) > _MAX_CANDIDATE_FEATURES:
            raise ValueError(
                f"features must contain at most {_MAX_CANDIDATE_FEATURES} values"
            )
        if any(not math.isfinite(value) for value in self.features):
            raise ValueError("features must contain only finite values")

    def semantic_key(self) -> tuple[object, ...]:
        tile = None if self.target_tile is None else (self.target_tile.x, self.target_tile.y)
        return (
            self.kind.value,
            self.target_entity_id,
            tile,
            self.inventory_slot,
            self.equipment_slot,
            self.belt_slot,
            self.spell_id,
            self.store_item_id,
            self.stat_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "kind": self.kind.value,
            "target_entity_id": self.target_entity_id,
            "target_tile": None if self.target_tile is None else self.target_tile.to_dict(),
            "inventory_slot": self.inventory_slot,
            "equipment_slot": self.equipment_slot,
            "belt_slot": self.belt_slot,
            "spell_id": self.spell_id,
            "store_item_id": self.store_item_id,
            "stat_id": self.stat_id,
            "label": self.label,
            "features": list(self.features),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ActionCandidate:
        tile = value.get("target_tile")
        result = cls(
            candidate_id=int(value["candidate_id"]),
            kind=ActionKind(value["kind"]),
            target_entity_id=_optional_int(value.get("target_entity_id")),
            target_tile=None if tile is None else Vec2.from_dict(tile),
            inventory_slot=_optional_int(value.get("inventory_slot")),
            equipment_slot=_optional_int(value.get("equipment_slot")),
            belt_slot=_optional_int(value.get("belt_slot")),
            spell_id=_optional_int(value.get("spell_id")),
            store_item_id=_optional_int(value.get("store_item_id")),
            stat_id=_optional_int(value.get("stat_id")),
            label=str(value.get("label", "")),
            features=tuple(float(item) for item in value.get("features", [])),
        )
        result.validate()
        return result


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)
