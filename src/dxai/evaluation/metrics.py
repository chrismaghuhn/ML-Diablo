from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EpisodeMetrics:
    episode_id: str
    task_id: str
    seed: int
    agent_name: str
    steps: int
    total_reward: float
    outcome: str
    success: bool
    terminated: bool
    truncated: bool
    player_hp: int
    player_hp_max: int
    action_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "task_id": self.task_id,
            "seed": self.seed,
            "agent_name": self.agent_name,
            "steps": self.steps,
            "total_reward": self.total_reward,
            "outcome": self.outcome,
            "success": self.success,
            "terminated": self.terminated,
            "truncated": self.truncated,
            "player_hp": self.player_hp,
            "player_hp_max": self.player_hp_max,
            "action_counts": self.action_counts,
        }


def aggregate_metrics(episodes: list[EpisodeMetrics]) -> dict[str, Any]:
    if not episodes:
        return {"episodes": 0}
    outcomes = Counter(item.outcome for item in episodes)
    return {
        "episodes": len(episodes),
        "success_rate": sum(item.success for item in episodes) / len(episodes),
        "mean_return": sum(item.total_reward for item in episodes) / len(episodes),
        "mean_steps": sum(item.steps for item in episodes) / len(episodes),
        "outcomes": dict(sorted(outcomes.items())),
        "seeds": [item.seed for item in episodes],
    }
