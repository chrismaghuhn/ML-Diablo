from __future__ import annotations

from collections import Counter
from pathlib import Path

from dxai.agents.base import Agent
from dxai.data.trajectory import EpisodeRecorder
from dxai.env.base import Environment
from dxai.evaluation.metrics import EpisodeMetrics


def run_episode(
    env: Environment,
    agent: Agent,
    *,
    seed: int,
    task_id: str,
    record_root: Path | None = None,
    data_source: str = "AGENT",
) -> EpisodeMetrics:
    observation = env.reset(seed=seed, task_id=task_id)
    agent.reset(seed)
    recorder = (
        EpisodeRecorder(
            record_root,
            observation,
            agent_name=agent.name,
            data_source=data_source,
        )
        if record_root is not None
        else None
    )
    total_reward = 0.0
    steps = 0
    action_counts: Counter[str] = Counter()
    outcome = "UNKNOWN"
    terminated = False
    truncated = False

    try:
        while True:
            candidate_id = agent.act(observation)
            action = observation.action_by_id(candidate_id)
            result = env.step(candidate_id)
            action_counts[action.kind.value] += 1
            if recorder is not None:
                recorder.record(
                    observation,
                    candidate_id,
                    result,
                    behavior={"agent_name": agent.name},
                )
            total_reward += result.reward
            steps += 1
            observation = result.observation
            outcome = str(result.info.get("outcome", "UNKNOWN"))
            terminated = result.terminated
            truncated = result.truncated
            if terminated or truncated:
                break
        if recorder is not None:
            recorder.close()
    except BaseException:
        if recorder is not None:
            recorder.abort()
        raise

    return EpisodeMetrics(
        episode_id=observation.episode_id,
        task_id=task_id,
        seed=seed,
        agent_name=agent.name,
        steps=steps,
        total_reward=total_reward,
        outcome=outcome,
        success=outcome == "SUCCESS",
        terminated=terminated,
        truncated=truncated,
        player_hp=observation.player.hp,
        player_hp_max=observation.player.hp_max,
        action_counts=dict(sorted(action_counts.items())),
    )
