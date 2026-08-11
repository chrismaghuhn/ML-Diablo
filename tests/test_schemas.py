from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from dxai.env.mock import DeterministicCombatEnv

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"


def _schema(name: str) -> dict[str, object]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _validator(name: str) -> Draft202012Validator:
    root = _schema(name)
    store = {
        _schema(file.name)["$id"]: _schema(file.name)
        for file in SCHEMA_DIR.glob("*.schema.json")
    }
    registry = Registry().with_resources(
        (uri, Resource.from_contents(value, default_specification=DRAFT202012))
        for uri, value in store.items()
    )
    return Draft202012Validator(root, registry=registry)


def test_runtime_observation_validates_against_schema() -> None:
    env = DeterministicCombatEnv()
    try:
        observation = env.reset(seed=5, task_id="combat.single_melee.v0")
    finally:
        env.close()
    _validator("observation.schema.json").validate(observation.to_dict())


def test_examples_validate() -> None:
    mapping = {
        "action.example.json": "action.schema.json",
        "observation.example.json": "observation.schema.json",
        "transition.example.json": "transition.schema.json",
        "episode_manifest.example.json": "episode_manifest.schema.json",
        "checkpoint.example.json": "checkpoint.schema.json",
    }
    for example, schema in mapping.items():
        value = json.loads((SCHEMA_DIR / "examples" / example).read_text(encoding="utf-8"))
        _validator(schema).validate(value)


def test_action_schema_rejects_cross_kind_payload_pollution() -> None:
    value = {
        "candidate_id": 0,
        "kind": "WAIT",
        "target_entity_id": 7,
        "target_tile": None,
        "inventory_slot": None,
        "equipment_slot": None,
        "belt_slot": None,
        "spell_id": None,
        "store_item_id": None,
        "stat_id": None,
        "label": "polluted wait",
        "features": [],
    }
    with pytest.raises(ValidationError):
        _validator("action.schema.json").validate(value)
