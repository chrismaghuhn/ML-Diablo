from __future__ import annotations

from dxai.contracts.actions import ActionCandidate


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
