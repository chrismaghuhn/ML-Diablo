#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from dxai.agents.heuristic_agent import HeuristicAgent
from dxai.data.trajectory import read_episode
from dxai.env.mock import DeterministicCombatEnv
from dxai.evaluation.runner import run_episode
from dxai.tasks.registry import list_tasks

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
LOCAL_LINK = re.compile(r"\[[^\]]+\]\((?!https?://|mailto:|#)([^)]+)\)")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def schema_store() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in SCHEMA_DIR.glob("*.schema.json"):
        schema = load_json(path)
        Draft202012Validator.check_schema(schema)
        result[str(schema["$id"])] = schema
    return result


def validator(name: str, store: dict[str, dict[str, Any]]) -> Draft202012Validator:
    schema = load_json(SCHEMA_DIR / name)
    registry = Registry().with_resources(
        (uri, Resource.from_contents(value, default_specification=DRAFT202012))
        for uri, value in store.items()
    )
    return Draft202012Validator(
        schema,
        registry=registry,
        format_checker=FormatChecker(),
    )


def validate_examples(store: dict[str, dict[str, Any]]) -> int:
    mapping = {
        "action.example.json": "action.schema.json",
        "observation.example.json": "observation.schema.json",
        "transition.example.json": "transition.schema.json",
        "probe_step.example.json": "probe_step.schema.json",
        "episode_manifest.example.json": "episode_manifest.schema.json",
        "checkpoint.example.json": "checkpoint.schema.json",
    }
    for example, schema in mapping.items():
        validator(schema, store).validate(load_json(SCHEMA_DIR / "examples" / example))
    return len(mapping)


def validate_runtime_episode(store: dict[str, dict[str, Any]]) -> tuple[int, int]:
    with tempfile.TemporaryDirectory(prefix="dxai-validation-") as temporary:
        root = Path(temporary)
        env = DeterministicCombatEnv()
        try:
            run_episode(
                env,
                HeuristicAgent(),
                seed=41,
                task_id="combat.single_melee.v0",
                record_root=root,
                data_source="SCRIPTED",
            )
        finally:
            env.close()
        directory = next(path for path in root.iterdir() if path.is_dir())
        manifest, records = read_episode(directory)
        validator("episode_manifest.schema.json", store).validate(manifest.to_dict())
        transition_validator = validator("transition.schema.json", store)
        action_validator = validator("action.schema.json", store)
        observation_validator = validator("observation.schema.json", store)
        for record in records:
            transition_validator.validate(record.to_dict())
            action_validator.validate(record.action.to_dict())
            observation_validator.validate(record.observation.to_dict())
            observation_validator.validate(record.next_observation.to_dict())
        return 1, len(records)


def validate_yaml() -> int:
    count = 0
    for path in sorted((ROOT / "configs").rglob("*.yaml")):
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"{path} must contain a YAML mapping")
        count += 1
    return count


def validate_local_markdown_links() -> int:
    count = 0
    roots = [ROOT / "README.md", ROOT / "PROJECT_STATUS.md", *sorted((ROOT / "docs").rglob("*.md"))]
    for source in roots:
        for raw_target in LOCAL_LINK.findall(source.read_text(encoding="utf-8")):
            target = raw_target.split("#", 1)[0].strip()
            if not target or target.startswith("<"):
                continue
            path = (source.parent / target).resolve()
            if not path.exists():
                raise FileNotFoundError(
                    f"broken local link in {source.relative_to(ROOT)}: {raw_target}"
                )
            count += 1
    return count


def validate_tasks() -> int:
    tasks = list_tasks()
    for task in tasks:
        task.validate()
    return len(tasks)


def main() -> int:
    store = schema_store()
    example_count = validate_examples(store)
    episode_count, transition_count = validate_runtime_episode(store)
    yaml_count = validate_yaml()
    link_count = validate_local_markdown_links()
    task_count = validate_tasks()
    print(
        "artifact validation OK: "
        f"schemas={len(store)} examples={example_count} runtime_episodes={episode_count} "
        f"runtime_transitions={transition_count} yaml={yaml_count} "
        f"local_links={link_count} tasks={task_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
