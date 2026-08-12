from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from dxai.contracts.common import Vec2
from dxai.contracts.serialization import canonical_json_bytes
from dxai.env.probe import ObservationProbe


def _required_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"set {name} to run the local DevilutionX M0.3 integration test")
    return Path(value)


def _sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _run_once(runtime_root: Path) -> dict[str, object]:
    probe = ObservationProbe(
        executable=_required_path("DXAI_M03_PROBE"),
        assets_path=_required_path("DXAI_DIABLO_DATA"),
        core_assets_path=_required_path("DXAI_DEVILUTIONX_CORE_ASSETS"),
        engine_runtime_path=_required_path("DXAI_DEVILUTIONX_RUNTIME"),
        runtime_root=runtime_root,
    )
    state = probe.start(seed=123, task_id="combat.single_melee.v0")
    initial = state.observation
    assert initial.legal_actions
    target = Vec2(initial.player.position.x + 1, initial.player.position.y + 1)
    selected = next(action for action in initial.legal_actions if action.target_tile == target)

    result = state.step(selected.candidate_id)
    assert result.requested_target_reached is True
    assert result.next_observation.legal_actions
    assert result.next_observation.player.position == target

    return {
        "initial_observation_sha256": _sha256_json(initial.to_dict()),
        "initial_candidate_set_sha256": result.candidate_set_sha256,
        "action_sha256": _sha256_json(selected.to_dict()),
        "next_observation_sha256": _sha256_json(result.next_observation.to_dict()),
        "next_candidate_set_sha256": result.next_candidate_set_sha256,
        "target_reached": result.requested_target_reached,
        "initial_candidate_count": len(initial.legal_actions),
        "next_candidate_count": len(result.next_observation.legal_actions),
    }


def test_real_m03_one_step_is_deterministic_across_clean_runtime_roots(
    tmp_path: Path,
) -> None:
    first = _run_once(tmp_path / "runtime-a")
    second = _run_once(tmp_path / "runtime-b")
    assert first == second
