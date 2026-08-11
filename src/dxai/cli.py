from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from dxai.agents.heuristic_agent import HeuristicAgent
from dxai.agents.random_agent import RandomAgent
from dxai.contracts.serialization import canonical_json
from dxai.data.trajectory import read_episode
from dxai.env.mock import DeterministicCombatEnv
from dxai.evaluation.metrics import aggregate_metrics
from dxai.evaluation.runner import run_episode
from dxai.tasks.registry import list_tasks
from dxai.training.r2d3 import R2D3Config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dxai", description="DevilutionX AI Lab scaffold")
    subparsers = parser.add_subparsers(dest="command", required=True)

    smoke = subparsers.add_parser("smoke", help="run deterministic mock episodes")
    smoke.add_argument("--episodes", type=int, default=3)
    smoke.add_argument("--agent", choices=("heuristic", "random"), default="heuristic")
    smoke.add_argument("--base-seed", type=int, default=0)
    smoke.add_argument("--task", default="combat.single_melee.v0")
    smoke.add_argument("--output", type=Path, default=None)
    smoke.add_argument("--no-record", action="store_true")

    inspect = subparsers.add_parser("inspect", help="verify and summarize one episode folder")
    inspect.add_argument("episode_directory", type=Path)

    subparsers.add_parser("tasks", help="list built-in task contracts")
    subparsers.add_parser("ml-plan", help="print the recommended training principle")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "smoke":
        return _smoke(args)
    if args.command == "inspect":
        return _inspect(args.episode_directory)
    if args.command == "tasks":
        for task in list_tasks():
            print(f"{task.task_id:32} {task.stage:4} {task.description}")
        return 0
    if args.command == "ml-plan":
        config = R2D3Config()
        config.validate()
        print(
            "R2D3-style recurrent off-policy Q-learning from demonstrations, "
            "preceded by behavior cloning and embedded in a staged skill hierarchy."
        )
        print(canonical_json({"starter_config": asdict(config)}))
        return 0
    raise AssertionError(f"unhandled command {args.command}")


def _smoke(args: argparse.Namespace) -> int:
    if args.episodes <= 0:
        raise SystemExit("--episodes must be positive")
    agent = HeuristicAgent() if args.agent == "heuristic" else RandomAgent()
    env = DeterministicCombatEnv()
    output = args.output or _default_output_directory()
    record_root = None if args.no_record else output / "episodes"
    if record_root is not None:
        record_root.mkdir(parents=True, exist_ok=True)

    episodes = []
    try:
        for index in range(args.episodes):
            metrics = run_episode(
                env,
                agent,
                seed=args.base_seed + index,
                task_id=args.task,
                record_root=record_root,
            )
            episodes.append(metrics)
            print(
                f"seed={metrics.seed} outcome={metrics.outcome} "
                f"steps={metrics.steps} return={metrics.total_reward:.4f}"
            )
    finally:
        env.close()

    summary = {
        "schema_version": "dxai.evaluation_summary.v1",
        "agent": agent.name,
        "task_id": args.task,
        "aggregate": aggregate_metrics(episodes),
        "episodes": [item.to_dict() for item in episodes],
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(canonical_json(summary) + "\n", encoding="utf-8")
    print(f"summary={output / 'summary.json'}")
    return 0


def _inspect(directory: Path) -> int:
    manifest, records = read_episode(directory)
    result = {
        "episode_id": manifest.episode_id,
        "task_id": manifest.task_id,
        "seed": manifest.seed,
        "agent_name": manifest.agent_name,
        "outcome": manifest.outcome,
        "steps": manifest.step_count,
        "return": manifest.total_reward,
        "first_action": None if not records else records[0].action.to_dict(),
        "last_step": None if not records else records[-1].step_id,
        "checksum_verified": True,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _default_output_directory() -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return Path("artifacts") / "smoke" / stamp
