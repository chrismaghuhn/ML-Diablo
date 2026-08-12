from __future__ import annotations

import hashlib

from dxai.contracts.actions import ActionCandidate

_OBSERVATION_CONTRACT_VERSION = "dxai.observation.v1"
_ACTION_CONTRACT_VERSION = "dxai.action.v1"
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


def assign_candidate_ids(actions: list[ActionCandidate]) -> tuple[ActionCandidate, ...]:
    """Sort semantic actions and assign deterministic, observation-local IDs."""
    keys = [action.semantic_key() for action in actions]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate semantic action candidates")
    sorted_actions = sorted(actions, key=ActionCandidate.semantic_key)
    result = tuple(
        ActionCandidate(
            candidate_id=index,
            kind=action.kind,
            target_entity_id=action.target_entity_id,
            target_tile=action.target_tile,
            inventory_slot=action.inventory_slot,
            equipment_slot=action.equipment_slot,
            belt_slot=action.belt_slot,
            spell_id=action.spell_id,
            store_item_id=action.store_item_id,
            stat_id=action.stat_id,
            label=action.label,
            features=action.features,
        )
        for index, action in enumerate(sorted_actions)
    )
    for action in result:
        action.validate()
    return result


def canonical_candidate_set_key(
    actions: tuple[ActionCandidate, ...] | list[ActionCandidate],
) -> str:
    """Return the stable semantic identity of one ordered candidate set.

    Labels and auxiliary features are deliberately excluded: they are descriptive
    fields, while candidate lifetime is defined by the contract versions, dense ID,
    kind, and closed semantic payload.
    """

    entries: list[str] = []
    semantic_keys: set[tuple[object, ...]] = set()
    for index, action in enumerate(actions):
        action.validate()
        if action.candidate_id != index:
            raise ValueError("candidate IDs must be dense and ordered")
        semantic_key = action.semantic_key()
        if semantic_key in semantic_keys:
            raise ValueError("duplicate semantic action candidates")
        semantic_keys.add(semantic_key)
        fields: list[str] = [
            f"candidate_id={action.candidate_id}",
            f"kind={action.kind.value}",
        ]
        for field in _PAYLOAD_FIELDS:
            value = getattr(action, field)
            if field == "target_tile":
                encoded = "null" if value is None else f"{value.x},{value.y}"
            else:
                encoded = "null" if value is None else str(value)
            fields.append(f"{field}={encoded}")
        entries.append(";".join(fields))
    return f"{_OBSERVATION_CONTRACT_VERSION}|{_ACTION_CONTRACT_VERSION}|" + "||".join(
        entries
    )


def candidate_set_sha256(actions: tuple[ActionCandidate, ...] | list[ActionCandidate]) -> str:
    return hashlib.sha256(canonical_candidate_set_key(actions).encode("utf-8")).hexdigest()
