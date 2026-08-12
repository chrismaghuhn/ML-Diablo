from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from dxai.contracts.actions import ActionCandidate, ActionKind
from dxai.contracts.common import Vec2
from dxai.contracts.observations import Observation
from dxai.data.engine_replay import (
    EngineReplayManifest,
    EngineReplayStep,
    SemanticAction,
    _loads_strict,
    load_engine_replay,
    publish_engine_replay,
)
from dxai.env.legal import candidate_set_sha256, canonical_action_key
from dxai.env.replay import (
    ReplayDivergence,
    play_engine_replay,
    record_engine_replay,
    semantic_observation_sha256,
)
from dxai.protocol.lifecycle import (
    ACTION_VERSION,
    ADAPTER_REVISION,
    BUILD_FINGERPRINT,
    DEVILUTIONX_REVISION,
    OBSERVATION_VERSION,
    PROCESS_PROTOCOL_VERSION,
    HealthResponse,
    PersistentStepResponse,
    ProcessState,
)


def test_canonical_action_key_excludes_candidate_id_label_and_features() -> None:
    first = ActionCandidate(
        candidate_id=0,
        kind=ActionKind.MOVE_TO_TILE,
        target_tile=Vec2(80, 59),
        label="east",
        features=(1.0,),
    )
    second = replace(first, candidate_id=7, label="renamed", features=(9.0, 8.0))

    assert canonical_action_key(first) == canonical_action_key(second)
    assert canonical_action_key(first) != canonical_action_key(
        replace(first, target_tile=Vec2(80, 60))
    )


def test_candidate_set_hash_uses_the_existing_canonical_format() -> None:
    action = ActionCandidate(
        candidate_id=0,
        kind=ActionKind.MOVE_TO_TILE,
        target_tile=Vec2(80, 59),
    )

    assert candidate_set_sha256([action]) == (
        "799c12aaacd1cdc034ec99df19aa514ec42706334c52a9475841cb4f0e04a155"
    )


def _fixture() -> tuple[EngineReplayManifest, tuple[EngineReplayStep, ...]]:
    action = SemanticAction(kind=ActionKind.MOVE_TO_TILE, target_tile=Vec2(80, 59))
    step = EngineReplayStep(
        step_id=0,
        observation_before_sha256="a" * 64,
        candidate_set_before_sha256="b" * 64,
        action=action,
        action_canonical_key=action.canonical_key,
        recorded_candidate_id=3,
        observation_after_sha256="c" * 64,
        candidate_set_after_sha256="d" * 64,
        engine_tick_before=0,
        engine_tick_after=10,
    )
    steps = (step,)
    manifest = EngineReplayManifest.create(
        task_id="combat.single_melee.v0",
        seed=123,
        devilutionx_revision="07385842840437cc9a785b195f5b40b121eaeb1c",
        adapter_revision="m0.4",
        build_fingerprint="dxai-ml-diablo-m0.4",
        asset_set_fingerprint="assets-test-v1",
        initial_observation_sha256="a" * 64,
        initial_candidate_set_sha256="b" * 64,
        steps=steps,
    )
    return manifest, steps


def test_engine_replay_artifact_round_trips_and_publishes_atomically(tmp_path: Path) -> None:
    manifest, steps = _fixture()
    destination = tmp_path / "replay"

    publish_engine_replay(destination, manifest, steps)

    loaded_manifest, loaded_steps = load_engine_replay(destination)
    assert loaded_manifest == manifest
    assert loaded_steps == steps
    assert {path.name for path in destination.iterdir()} == {"manifest.json", "steps.jsonl"}
    assert not list(tmp_path.glob(".replay.tmp-*"))


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda value: value.update({"unexpected": True}), "unknown field"),
        (lambda value: value.update({"steps_file": "../steps.jsonl"}), "steps_file"),
    ],
)
def test_engine_replay_manifest_rejects_unsafe_or_unknown_fields(
    mutator, message: str
) -> None:
    manifest, _ = _fixture()
    value = manifest.to_dict()
    mutator(value)

    with pytest.raises(ValueError, match=message):
        EngineReplayManifest.from_dict(value)


def test_engine_replay_manifest_rejects_currently_incompatible_identity() -> None:
    manifest, _ = _fixture()

    with pytest.raises(ValueError, match="incompatible devilutionx_revision"):
        replace(manifest, devilutionx_revision="different-revision").validate()


def test_engine_replay_rejects_non_contiguous_steps(tmp_path: Path) -> None:
    manifest, steps = _fixture()
    bad_step = replace(steps[0], step_id=2)

    with pytest.raises(ValueError, match="contiguous"):
        publish_engine_replay(tmp_path / "replay", manifest, (bad_step,))


def test_engine_replay_rejects_checksum_tampering(tmp_path: Path) -> None:
    manifest, steps = _fixture()
    destination = tmp_path / "replay"
    publish_engine_replay(destination, manifest, steps)
    steps_path = destination / "steps.jsonl"
    steps_path.write_text(
        steps_path.read_text(encoding="utf-8").replace(
            '"engine_tick_after":10', '"engine_tick_after":11'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="checksum"):
        load_engine_replay(destination)


@pytest.mark.parametrize(
    "raw",
    [
        '{"step_id":0,"step_id":0}',
        '{"step_id":0,"engine_tick_before":NaN}',
        '{"step_id":0,"engine_tick_before":Infinity}',
    ],
)
def test_engine_replay_rejects_duplicate_keys_and_non_finite_json(raw: str) -> None:
    with pytest.raises(ValueError):
        _loads_strict(raw)


def test_engine_replay_rejects_symlinked_steps_file_when_supported(tmp_path: Path) -> None:
    manifest, steps = _fixture()
    destination = tmp_path / "replay"
    publish_engine_replay(destination, manifest, steps)
    original = destination / "steps.jsonl"
    replacement = destination / "steps-target.jsonl"
    original.rename(replacement)
    try:
        original.symlink_to(replacement)
    except (OSError, NotImplementedError):
        replacement.rename(original)
        pytest.skip("symlink creation is unavailable on this Windows host")

    with pytest.raises(ValueError, match="symlink"):
        load_engine_replay(destination)


def test_engine_replay_rejects_unexpected_artifact_files(tmp_path: Path) -> None:
    manifest, steps = _fixture()
    destination = tmp_path / "replay"
    publish_engine_replay(destination, manifest, steps)
    (destination / "unexpected.bin").write_bytes(b"not part of the artifact")

    with pytest.raises(ValueError, match="unexpected"):
        load_engine_replay(destination)


def _observations():
    payload = json.loads(
        (Path(__file__).parents[1] / "schemas/examples/probe_step.example.json").read_text(
            encoding="utf-8"
        )
    )
    return (
        Observation.from_dict(payload["observation"]),
        Observation.from_dict(payload["next_observation"]),
    )


class _ReplayEnvironment:
    def __init__(self) -> None:
        first, second = _observations()
        self._first = replace(first, episode_id="recorded-episode", seed=123)
        self._second = replace(second, episode_id="recorded-episode", seed=123, step_id=1)
        self.health = HealthResponse(
            request_id=1,
            process_state=ProcessState.READY,
            adapter_revision=ADAPTER_REVISION,
            devilutionx_revision=DEVILUTIONX_REVISION,
            build_fingerprint=BUILD_FINGERPRINT,
            observation_version=OBSERVATION_VERSION,
            action_version=ACTION_VERSION,
            supported_task_versions=("combat.single_melee.v0",),
            supported_features=("MOVE_TO_TILE", "cold_reset", "request_idempotency"),
            pid=9001,
            protocol_version=PROCESS_PROTOCOL_VERSION,
        )
        self.observation = None
        self.sent_candidate_ids: list[int] = []
        self.response_candidate_set_sha256: str | None = None

    def reset(self, *, seed: int, task_id: str):
        assert seed == 123
        assert task_id == "combat.single_melee.v0"
        self.observation = replace(self._first, episode_id="fresh-episode")
        return self.observation

    def step(self, candidate_id: int) -> PersistentStepResponse:
        assert self.observation is not None
        self.sent_candidate_ids.append(candidate_id)
        action = self.observation.action_by_id(candidate_id)
        response = PersistentStepResponse(
            request_id=2,
            episode_id=self.observation.episode_id,
            previous_step_id=self.observation.step_id,
            applied_action=action,
            previous_candidate_set_sha256=candidate_set_sha256(
                self.observation.legal_actions
            ),
            observation=replace(self._second, episode_id=self.observation.episode_id),
            candidate_set_sha256=(
                self.response_candidate_set_sha256
                or candidate_set_sha256(self._second.legal_actions)
            ),
            process_state=ProcessState.EPISODE_ACTIVE,
        )
        self.observation = response.observation
        return response


def _playback_fixture() -> tuple[EngineReplayManifest, tuple[EngineReplayStep, ...]]:
    environment = _ReplayEnvironment()
    assert environment.observation is None
    initial = replace(environment._first, episode_id="recorded-episode")
    next_observation = environment._second
    selected = initial.legal_actions[0]
    step = EngineReplayStep(
        step_id=0,
        observation_before_sha256=semantic_observation_sha256(initial),
        candidate_set_before_sha256=candidate_set_sha256(initial.legal_actions),
        action=SemanticAction.from_candidate(selected),
        action_canonical_key=canonical_action_key(selected),
        recorded_candidate_id=3,
        observation_after_sha256=semantic_observation_sha256(next_observation),
        candidate_set_after_sha256=candidate_set_sha256(next_observation.legal_actions),
        engine_tick_before=initial.engine_tick,
        engine_tick_after=next_observation.engine_tick,
    )
    manifest = EngineReplayManifest.create(
        task_id=initial.task_id,
        seed=initial.seed,
        devilutionx_revision=DEVILUTIONX_REVISION,
        adapter_revision=ADAPTER_REVISION,
        build_fingerprint=BUILD_FINGERPRINT,
        asset_set_fingerprint="assets-test-v1",
        initial_observation_sha256=step.observation_before_sha256,
        initial_candidate_set_sha256=step.candidate_set_before_sha256,
        steps=(step,),
    )
    return manifest, (step,)


def test_playback_resolves_semantic_action_and_ignores_recorded_candidate_id() -> None:
    manifest, steps = _playback_fixture()
    environment = _ReplayEnvironment()

    trace_hash = play_engine_replay(
        environment,
        manifest,
        steps,
        asset_set_fingerprint="assets-test-v1",
    )

    assert trace_hash == manifest.semantic_trace_sha256
    assert environment.sent_candidate_ids == [0]


@pytest.mark.parametrize(
    ("component", "expected_component"),
    [
        ("semantic_action", "semantic_action"),
        ("candidate_set_before_sha256", "initial_candidate_set_sha256"),
        ("observation_before_sha256", "initial_observation_sha256"),
    ],
)
def test_playback_stops_before_step_on_precondition_divergence(
    component: str, expected_component: str
) -> None:
    manifest, steps = _playback_fixture()
    step = steps[0]
    if component == "semantic_action":
        action = replace(step.action, target_tile=Vec2(99, 99))
        changed = replace(step, action=action, action_canonical_key=action.canonical_key)
    elif component == "candidate_set_before_sha256":
        changed = replace(step, candidate_set_before_sha256="e" * 64)
    else:
        changed = replace(step, observation_before_sha256="e" * 64)
    changed_manifest = EngineReplayManifest.create(
        task_id=manifest.task_id,
        seed=manifest.seed,
        devilutionx_revision=manifest.devilutionx_revision,
        adapter_revision=manifest.adapter_revision,
        build_fingerprint=manifest.build_fingerprint,
        asset_set_fingerprint=manifest.asset_set_fingerprint,
        initial_observation_sha256=changed.observation_before_sha256,
        initial_candidate_set_sha256=changed.candidate_set_before_sha256,
        steps=(changed,),
    )
    environment = _ReplayEnvironment()

    with pytest.raises(ReplayDivergence) as error:
        play_engine_replay(
            environment,
            changed_manifest,
            (changed,),
            asset_set_fingerprint="assets-test-v1",
        )

    assert error.value.step_id == 0
    assert error.value.component == expected_component
    assert environment.sent_candidate_ids == []


def test_playback_reports_post_observation_divergence_after_one_step() -> None:
    manifest, steps = _playback_fixture()
    changed = replace(steps[0], observation_after_sha256="e" * 64)
    changed_manifest = EngineReplayManifest.create(
        task_id=manifest.task_id,
        seed=manifest.seed,
        devilutionx_revision=manifest.devilutionx_revision,
        adapter_revision=manifest.adapter_revision,
        build_fingerprint=manifest.build_fingerprint,
        asset_set_fingerprint=manifest.asset_set_fingerprint,
        initial_observation_sha256=changed.observation_before_sha256,
        initial_candidate_set_sha256=changed.candidate_set_before_sha256,
        steps=(changed,),
    )
    environment = _ReplayEnvironment()

    with pytest.raises(ReplayDivergence) as error:
        play_engine_replay(
            environment,
            changed_manifest,
            (changed,),
            asset_set_fingerprint="assets-test-v1",
        )

    assert error.value.component == "observation_after_sha256"
    assert environment.sent_candidate_ids == [0]


def test_playback_rejects_response_candidate_hash_not_matching_observation() -> None:
    manifest, steps = _playback_fixture()
    environment = _ReplayEnvironment()
    environment.response_candidate_set_sha256 = "e" * 64

    with pytest.raises(ReplayDivergence) as error:
        play_engine_replay(
            environment,
            manifest,
            steps,
            asset_set_fingerprint="assets-test-v1",
        )

    assert error.value.component == "response_candidate_set_after_sha256"


def test_playback_rejects_incompatible_manifest_before_reset() -> None:
    manifest, steps = _playback_fixture()
    incompatible = replace(manifest, devilutionx_revision="wrong-revision")
    environment = _ReplayEnvironment()

    with pytest.raises(ValueError, match="devilutionx_revision"):
        play_engine_replay(
            environment,
            incompatible,
            steps,
            asset_set_fingerprint="assets-test-v1",
        )

    assert environment.observation is None


def test_record_engine_replay_publishes_full_semantic_action_payload(tmp_path: Path) -> None:
    environment = _ReplayEnvironment()

    manifest = record_engine_replay(
        environment,
        tmp_path / "recorded",
        seed=123,
        task_id="combat.single_melee.v0",
        asset_set_fingerprint="assets-test-v1",
        select_candidate=lambda observation: observation.legal_actions[0].candidate_id,
        max_steps=1,
    )

    loaded_manifest, loaded_steps = load_engine_replay(tmp_path / "recorded")
    assert loaded_manifest == manifest
    assert loaded_steps[0].action.to_dict()["kind"] == "MOVE_TO_TILE"
    assert "target_tile" in loaded_steps[0].action.to_dict()
    assert "candidate_id" not in loaded_steps[0].action.to_dict()


def test_record_engine_replay_rejects_incompatible_health_identity(tmp_path: Path) -> None:
    environment = _ReplayEnvironment()
    environment.health = replace(environment.health, build_fingerprint="different-build")

    with pytest.raises(ValueError, match="incompatible"):
        record_engine_replay(
            environment,
            tmp_path / "recorded",
            seed=123,
            task_id="combat.single_melee.v0",
            asset_set_fingerprint="assets-test-v1",
            select_candidate=lambda observation: observation.legal_actions[0].candidate_id,
            max_steps=1,
        )
