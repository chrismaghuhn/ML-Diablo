from __future__ import annotations

import pytest

from dxai.agents.heuristic_agent import HeuristicAgent
from dxai.contracts.common import Vec2
from dxai.contracts.serialization import canonical_json
from dxai.env.mock import DeterministicCombatEnv


def _rollout(seed: int) -> list[dict[str, object]]:
    env = DeterministicCombatEnv()
    agent = HeuristicAgent()
    observation = env.reset(seed=seed, task_id="combat.single_melee.v0")
    agent.reset(seed)
    result: list[dict[str, object]] = [observation.to_dict()]
    try:
        while True:
            step = env.step(agent.act(observation))
            result.append(
                {
                    "reward": step.reward,
                    "terminated": step.terminated,
                    "truncated": step.truncated,
                    "info": step.info,
                    "observation": step.observation.to_dict(),
                }
            )
            observation = step.observation
            if step.terminated or step.truncated:
                break
    finally:
        env.close()
    return result


def test_same_seed_and_policy_are_byte_deterministic() -> None:
    left = canonical_json(_rollout(77))
    right = canonical_json(_rollout(77))
    assert left == right


def test_different_seeds_exercise_variation() -> None:
    assert canonical_json(_rollout(1)) != canonical_json(_rollout(2))


def test_heuristic_solves_seed_set() -> None:
    for seed in range(20):
        rollout = _rollout(seed)
        final = rollout[-1]
        assert isinstance(final, dict)
        assert final["info"]["outcome"] == "SUCCESS"  # type: ignore[index]


def test_invalid_action_does_not_advance_state() -> None:
    env = DeterministicCombatEnv()
    try:
        before = env.reset(seed=4, task_id="combat.single_melee.v0")
        with pytest.raises(KeyError):
            env.step(999)
        after = env._observation("PLAYER_READY")  # contract-level test of mock only
        assert before.step_id == after.step_id
        assert before.player == after.player
    finally:
        env.close()


def test_terminal_step_requires_reset() -> None:
    env = DeterministicCombatEnv()
    agent = HeuristicAgent()
    observation = env.reset(seed=8, task_id="combat.single_melee.v0")
    agent.reset(8)
    try:
        while True:
            result = env.step(agent.act(observation))
            observation = result.observation
            if result.terminated or result.truncated:
                break
        with pytest.raises(RuntimeError, match="already finished"):
            env.step(0)
    finally:
        env.close()


def test_dead_monster_does_not_leave_ghost_occupancy() -> None:
    env = DeterministicCombatEnv()
    agent = HeuristicAgent()
    observation = env.reset(seed=6, task_id="combat.single_melee.v0")
    agent.reset(6)
    try:
        while True:
            result = env.step(agent.act(observation))
            observation = result.observation
            if result.terminated or result.truncated:
                break
        assert result.info["outcome"] == "SUCCESS"
        relative = Vec2(
            env._monster.position.x - observation.player.position.x,
            env._monster.position.y - observation.player.position.y,
        )
        monster_tile = next(
            tile for tile in observation.local_tiles if tile.relative == relative
        )
        assert not monster_tile.occupied
    finally:
        env.close()
