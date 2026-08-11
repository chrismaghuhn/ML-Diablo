from __future__ import annotations

import random
from dataclasses import dataclass

from dxai.contracts.actions import ActionCandidate, ActionKind
from dxai.contracts.common import Vec2
from dxai.contracts.observations import (
    EntityKind,
    EntityState,
    Observation,
    PlayerState,
    TileCell,
)
from dxai.contracts.results import StepResult
from dxai.env.base import Environment
from dxai.env.legal import assign_candidate_ids


@dataclass(slots=True)
class _Monster:
    entity_id: int
    position: Vec2
    hp: int
    hp_max: int


class DeterministicCombatEnv(Environment):
    """Small deterministic contract environment; it is not a Diablo simulator.

    It exercises partial observability, semantic legal actions, stochastic combat,
    terminal handling and trajectory round-trips before an upstream engine is linked.
    """

    width = 9
    height = 9
    vision_radius = 3

    def __init__(self, *, max_steps: int = 160) -> None:
        self.max_steps = max_steps
        self._rng = random.Random()
        self._reset_index = 0
        self._episode_id = "uninitialized"
        self._task_id = "uninitialized"
        self._seed = 0
        self._step_id = 0
        self._engine_tick = 0
        self._player_pos = Vec2(1, 1)
        self._player_hp = 20
        self._player_hp_max = 20
        self._potions = 0
        self._monster = _Monster(100, Vec2(7, 7), 12, 12)
        self._potion_pos: Vec2 | None = Vec2(2, 1)
        self._explored: set[Vec2] = set()
        self._recent_events: list[str] = []
        self._terminated = False
        self._truncated = False

    def reset(self, *, seed: int, task_id: str) -> Observation:
        if task_id != "combat.single_melee.v0":
            raise ValueError(f"mock environment does not implement task {task_id!r}")
        self._rng.seed(seed)
        self._seed = seed
        self._task_id = task_id
        self._episode_id = f"mock-{task_id}-{seed}-{self._reset_index:04d}"
        self._reset_index += 1
        self._step_id = 0
        self._engine_tick = 0
        self._player_pos = Vec2(1, 1)
        self._player_hp = 20
        self._player_hp_max = 20
        self._potions = 0
        monster_positions = [Vec2(7, 7), Vec2(6, 7), Vec2(7, 6)]
        self._monster = _Monster(100, self._rng.choice(monster_positions), 12, 12)
        self._potion_pos = Vec2(2, 1)
        self._explored = set()
        self._recent_events = ["EPISODE_RESET"]
        self._terminated = False
        self._truncated = False
        return self._observation("RESET")

    def step(self, candidate_id: int) -> StepResult:
        if self._terminated or self._truncated:
            raise RuntimeError("episode is already finished; call reset")

        current = self._observation("PLAYER_READY")
        action = current.action_by_id(candidate_id)
        old_player_hp = self._player_hp
        old_monster_hp = self._monster.hp
        explored_before = len(self._explored)
        potions_before = self._potions
        events: list[str] = []

        self._apply_player_action(action, events)
        if self._monster.hp > 0:
            self._apply_monster_turn(events)

        self._step_id += 1
        self._engine_tick += 1
        self._terminated = self._monster.hp <= 0 or self._player_hp <= 0
        self._truncated = self._step_id >= self.max_steps and not self._terminated
        self._recent_events = events[-8:]

        # Calling _observation updates the remembered explored set.
        reason = "TERMINAL" if self._terminated or self._truncated else "PLAYER_READY"
        observation = self._observation(reason)
        damage_dealt = max(0, old_monster_hp - self._monster.hp)
        damage_taken = max(0, old_player_hp - self._player_hp)
        newly_explored = max(0, len(self._explored) - explored_before)
        picked_potion = int(self._potions > potions_before)

        reward_components = {
            "living_cost": -0.001,
            "damage_dealt": 0.02 * damage_dealt,
            "damage_taken": -0.02 * damage_taken,
            "newly_explored": 0.001 * newly_explored,
            "picked_potion": 0.02 * picked_potion,
            "success": 1.0 if self._monster.hp <= 0 else 0.0,
            "death": -1.0 if self._player_hp <= 0 else 0.0,
        }
        reward = sum(reward_components.values())

        outcome = "ONGOING"
        if self._monster.hp <= 0:
            outcome = "SUCCESS"
        elif self._player_hp <= 0:
            outcome = "DEATH"
        elif self._truncated:
            outcome = "TIME_LIMIT"

        result = StepResult(
            observation=observation,
            reward=reward,
            terminated=self._terminated,
            truncated=self._truncated,
            info={
                "outcome": outcome,
                "damage_dealt": damage_dealt,
                "damage_taken": damage_taken,
                "newly_explored": newly_explored,
                "events": events,
                "reward_components": reward_components,
            },
        )
        result.validate()
        return result

    def close(self) -> None:
        return None

    def _apply_player_action(self, action: ActionCandidate, events: list[str]) -> None:
        if action.kind is ActionKind.WAIT:
            events.append("PLAYER_WAITED")
            return
        if action.kind is ActionKind.MOVE_TO_TILE:
            assert action.target_tile is not None
            self._player_pos = action.target_tile
            events.append(f"PLAYER_MOVED:{action.target_tile.x},{action.target_tile.y}")
            return
        if action.kind is ActionKind.ATTACK_ENTITY:
            if action.target_entity_id != self._monster.entity_id:
                raise ValueError("unknown attack target")
            if self._player_pos.manhattan(self._monster.position) != 1:
                raise ValueError("attack target is not adjacent")
            damage = self._rng.randint(3, 5)
            self._monster.hp = max(0, self._monster.hp - damage)
            events.append(f"PLAYER_HIT:{damage}")
            return
        if action.kind is ActionKind.PICK_UP_ITEM:
            if self._potion_pos != self._player_pos:
                raise ValueError("item is not on player tile")
            self._potion_pos = None
            self._potions += 1
            events.append("POTION_PICKED_UP")
            return
        if action.kind is ActionKind.USE_BELT_SLOT:
            if self._potions <= 0 or self._player_hp >= self._player_hp_max:
                raise ValueError("potion is not usable")
            self._potions -= 1
            healed = min(8, self._player_hp_max - self._player_hp)
            self._player_hp += healed
            events.append(f"POTION_USED:{healed}")
            return
        raise ValueError(f"unsupported mock action {action.kind}")

    def _apply_monster_turn(self, events: list[str]) -> None:
        distance = self._monster.position.manhattan(self._player_pos)
        if distance == 1:
            damage = self._rng.randint(1, 3)
            self._player_hp = max(0, self._player_hp - damage)
            events.append(f"MONSTER_HIT:{damage}")
            return

        old_position = self._monster.position
        dx = 0 if old_position.x == self._player_pos.x else (
            -1 if old_position.x > self._player_pos.x else 1
        )
        dy = 0 if old_position.y == self._player_pos.y else (
            -1 if old_position.y > self._player_pos.y else 1
        )
        candidates: list[Vec2] = []
        if dx != 0:
            candidates.append(Vec2(old_position.x + dx, old_position.y))
        if dy != 0:
            candidates.append(Vec2(old_position.x, old_position.y + dy))
        for position in candidates:
            if position != self._player_pos and self._is_walkable(position):
                self._monster.position = position
                if self._visible(old_position) or self._visible(position):
                    events.append(f"MONSTER_MOVED:{position.x},{position.y}")
                return

    def _legal_actions(self) -> tuple[ActionCandidate, ...]:
        actions = [ActionCandidate(-1, ActionKind.WAIT, label="Wait")]
        for delta in (Vec2(0, -1), Vec2(1, 0), Vec2(0, 1), Vec2(-1, 0)):
            target = Vec2(self._player_pos.x + delta.x, self._player_pos.y + delta.y)
            if self._is_walkable(target) and target != self._monster.position:
                actions.append(
                    ActionCandidate(
                        -1,
                        ActionKind.MOVE_TO_TILE,
                        target_tile=target,
                        label=f"Move to {target.x},{target.y}",
                        features=(float(delta.x), float(delta.y), 0.0),
                    )
                )
        if self._monster.hp > 0 and self._player_pos.manhattan(self._monster.position) == 1:
            actions.append(
                ActionCandidate(
                    -1,
                    ActionKind.ATTACK_ENTITY,
                    target_entity_id=self._monster.entity_id,
                    label="Attack monster",
                    features=(0.0, 0.0, self._monster.hp / self._monster.hp_max),
                )
            )
        if self._potion_pos == self._player_pos:
            actions.append(
                ActionCandidate(
                    -1,
                    ActionKind.PICK_UP_ITEM,
                    target_entity_id=200,
                    label="Pick up potion",
                    features=(0.0, 0.0, 1.0),
                )
            )
        if self._potions > 0 and self._player_hp < self._player_hp_max:
            actions.append(
                ActionCandidate(
                    -1,
                    ActionKind.USE_BELT_SLOT,
                    belt_slot=0,
                    label="Use healing potion",
                    features=(0.0, 0.0, self._player_hp / self._player_hp_max),
                )
            )
        return assign_candidate_ids(actions)

    def _observation(self, reason: str) -> Observation:
        for y in range(self.height):
            for x in range(self.width):
                position = Vec2(x, y)
                if self._visible(position):
                    self._explored.add(position)

        entities: list[EntityState] = []
        if self._monster.hp > 0 and self._visible(self._monster.position):
            entities.append(
                EntityState(
                    entity_id=self._monster.entity_id,
                    kind=EntityKind.MONSTER,
                    position=self._monster.position,
                    type_id="MOCK_ZOMBIE",
                    hp=self._monster.hp,
                    hp_max=self._monster.hp_max,
                    hostile=True,
                )
            )
        if self._potion_pos is not None and self._visible(self._potion_pos):
            entities.append(
                EntityState(
                    entity_id=200,
                    kind=EntityKind.ITEM,
                    position=self._potion_pos,
                    type_id="HEALING_POTION",
                )
            )

        tiles: list[TileCell] = []
        for y in range(self.height):
            for x in range(self.width):
                absolute = Vec2(x, y)
                visible = self._visible(absolute)
                explored = absolute in self._explored
                known_walkable = self._is_walkable(absolute) if explored else False
                living_monster_position = (
                    self._monster.position if self._monster.hp > 0 else None
                )
                occupied = visible and absolute in {
                    self._player_pos,
                    living_monster_position,
                }
                tiles.append(
                    TileCell(
                        relative=Vec2(x - self._player_pos.x, y - self._player_pos.y),
                        terrain_id=(1 if known_walkable else 0) if explored else -1,
                        walkable=known_walkable,
                        visible=visible,
                        explored=explored,
                        occupied=occupied,
                    )
                )

        terminal = self._terminated or self._truncated
        actions = (
            ActionCandidate(0, ActionKind.WAIT, label="Terminal no-op"),
        ) if terminal else self._legal_actions()
        result = Observation(
            schema_version="dxai.observation.v1",
            episode_id=self._episode_id,
            task_id=self._task_id,
            seed=self._seed,
            step_id=self._step_id,
            engine_tick=self._engine_tick,
            decision_reason=reason,
            player=PlayerState(
                position=self._player_pos,
                hp=self._player_hp,
                hp_max=self._player_hp_max,
                potions=self._potions,
            ),
            local_tiles=tuple(tiles),
            entities=tuple(sorted(entities, key=lambda entity: entity.entity_id)),
            legal_actions=actions,
            recent_events=tuple(self._recent_events),
        )
        result.validate()
        return result

    def _visible(self, position: Vec2) -> bool:
        return self._player_pos.manhattan(position) <= self.vision_radius

    def _is_walkable(self, position: Vec2) -> bool:
        return 0 < position.x < self.width - 1 and 0 < position.y < self.height - 1
