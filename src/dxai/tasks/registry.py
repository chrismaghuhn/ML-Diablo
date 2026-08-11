from __future__ import annotations

from dxai.contracts.actions import ActionKind
from dxai.tasks.spec import TaskSpec

_BUILT_INS = {
    "combat.single_melee.v0": TaskSpec(
        task_id="combat.single_melee.v0",
        stage="M1",
        description="Defeat one melee monster in a bounded arena and survive.",
        max_decisions=160,
        allowed_action_kinds=(
            ActionKind.WAIT,
            ActionKind.MOVE_TO_TILE,
            ActionKind.ATTACK_ENTITY,
            ActionKind.PICK_UP_ITEM,
            ActionKind.USE_BELT_SLOT,
        ),
        success_condition="target monster is dead and player HP is positive",
        failure_conditions=("player death", "decision limit"),
        reward_version="combat.reward.v1",
        train_seed_range=(0, 9999),
        validation_seeds=tuple(range(10000, 10032)),
        test_seeds=tuple(range(20000, 20128)),
    ),
    "explore.find_stairs.v0": TaskSpec(
        task_id="explore.find_stairs.v0",
        stage="M3",
        description="Explore a generated level and reach visible stairs without combat.",
        max_decisions=800,
        allowed_action_kinds=(
            ActionKind.WAIT,
            ActionKind.MOVE_TO_TILE,
            ActionKind.OPERATE_OBJECT,
            ActionKind.TAKE_STAIRS,
        ),
        success_condition="stairs transition accepted by engine",
        failure_conditions=("player death", "decision limit", "engine fault"),
        reward_version="exploration.reward.v1",
        train_seed_range=(30000, 39999),
        validation_seeds=tuple(range(40000, 40032)),
        test_seeds=tuple(range(50000, 50128)),
    ),
    "fullrun.warrior.normal.v0": TaskSpec(
        task_id="fullrun.warrior.normal.v0",
        stage="M8",
        description="Fresh Warrior to Diablo kill on Normal difficulty.",
        max_decisions=100000,
        allowed_action_kinds=tuple(ActionKind),
        success_condition="Diablo defeated by the controlled character",
        failure_conditions=("permadeath policy", "run time limit", "engine fault"),
        reward_version="fullrun.reward.v1",
        train_seed_range=(100000, 199999),
        validation_seeds=tuple(range(200000, 200032)),
        test_seeds=tuple(range(300000, 300128)),
    ),
}

for _task in _BUILT_INS.values():
    _task.validate()


def get_task(task_id: str) -> TaskSpec:
    try:
        return _BUILT_INS[task_id]
    except KeyError as error:
        raise KeyError(f"unknown task {task_id!r}") from error


def list_tasks() -> tuple[TaskSpec, ...]:
    return tuple(_BUILT_INS[key] for key in sorted(_BUILT_INS))
