from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol

from dxai.contracts.observations import Observation
from dxai.data.engine_replay import (
    EngineReplayManifest,
    EngineReplayStep,
    SemanticAction,
    load_engine_replay,
    publish_engine_replay,
    semantic_trace_sha256,
    validate_engine_replay,
)
from dxai.env.determinism import canonical_trace_sha256
from dxai.env.legal import candidate_set_sha256, canonical_action_key
from dxai.protocol.lifecycle import (
    ADAPTER_REVISION,
    BUILD_FINGERPRINT,
    DEVILUTIONX_REVISION,
    PROCESS_PROTOCOL_VERSION,
    HealthResponse,
    PersistentStepResponse,
    ProcessErrorCode,
)
from dxai.protocol.messages import ACTION_VERSION, OBSERVATION_VERSION


class ReplayEnvironment(Protocol):
    health: HealthResponse | None
    observation: Observation | None

    def reset(self, *, seed: int, task_id: str) -> Observation: ...

    def step(self, candidate_id: int) -> PersistentStepResponse: ...


class ReplayDivergence(ValueError):
    """The first reproducibility mismatch found during engine replay."""

    code = ProcessErrorCode.REPLAY_DIVERGENCE

    def __init__(
        self,
        *,
        step_id: int,
        component: str,
        expected: object,
        actual: object,
    ) -> None:
        self.step_id = step_id
        self.component = component
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"REPLAY_DIVERGENCE at step {step_id} component {component}: "
            f"expected={expected!r} actual={actual!r}"
        )


def semantic_observation_sha256(observation: Observation) -> str:
    """Hash an observation while excluding only documented lifecycle metadata."""

    observation.validate()
    return canonical_trace_sha256(observation.to_dict())


def validate_replay_compatibility(
    manifest: EngineReplayManifest,
    *,
    task_id: str,
    seed: int,
    asset_set_fingerprint: str,
) -> None:
    manifest.validate()
    expected = {
        "schema_version": "dxai.engine_replay.v1",
        "task_id": task_id,
        "seed": seed,
        "devilutionx_revision": DEVILUTIONX_REVISION,
        "adapter_revision": ADAPTER_REVISION,
        "build_fingerprint": BUILD_FINGERPRINT,
        "process_protocol_version": PROCESS_PROTOCOL_VERSION,
        "observation_version": OBSERVATION_VERSION,
        "action_version": ACTION_VERSION,
        "candidate_canonicalization_version": "dxai.candidate_set.v1",
        "asset_set_fingerprint": asset_set_fingerprint,
    }
    for component, expected_value in expected.items():
        actual_value = getattr(manifest, component)
        if actual_value != expected_value:
            raise ValueError(
                f"incompatible replay {component}: "
                f"expected {expected_value!r}, got {actual_value!r}"
            )


def play_engine_replay(
    environment: ReplayEnvironment,
    manifest_or_path: EngineReplayManifest | Path,
    steps: Sequence[EngineReplayStep] | None = None,
    *,
    asset_set_fingerprint: str,
) -> str:
    """Replay semantic actions against a fresh environment and return its trace hash."""

    if isinstance(manifest_or_path, Path):
        manifest, loaded_steps = load_engine_replay(manifest_or_path)
        replay_steps = loaded_steps if steps is None else tuple(steps)
    else:
        manifest = manifest_or_path
        if steps is None:
            raise ValueError("steps are required when a manifest object is supplied")
        replay_steps = tuple(steps)

    validate_engine_replay(manifest, replay_steps)
    validate_replay_compatibility(
        manifest,
        task_id=manifest.task_id,
        seed=manifest.seed,
        asset_set_fingerprint=asset_set_fingerprint,
    )

    observation = environment.reset(seed=manifest.seed, task_id=manifest.task_id)
    health = environment.health
    if health is None:
        raise ValueError("replay environment did not expose a Health response")
    _validate_health_against_manifest(health, manifest)
    _expect(
        0,
        "initial_observation_sha256",
        manifest.initial_observation_sha256,
        semantic_observation_sha256(observation),
    )
    _expect(
        0,
        "initial_candidate_set_sha256",
        manifest.initial_candidate_set_sha256,
        candidate_set_sha256(observation.legal_actions),
    )

    actual_steps: list[EngineReplayStep] = []
    for expected in replay_steps:
        _expect(expected.step_id, "step_id", expected.step_id, observation.step_id)
        _expect(
            expected.step_id,
            "observation_before_sha256",
            expected.observation_before_sha256,
            semantic_observation_sha256(observation),
        )
        current_candidate_hash = candidate_set_sha256(observation.legal_actions)
        _expect(
            expected.step_id,
            "candidate_set_before_sha256",
            expected.candidate_set_before_sha256,
            current_candidate_hash,
        )

        matches = [
            candidate
            for candidate in observation.legal_actions
            if canonical_action_key(candidate) == expected.action_canonical_key
            and SemanticAction.from_candidate(candidate).to_dict() == expected.action.to_dict()
        ]
        if len(matches) != 1:
            raise ReplayDivergence(
                step_id=expected.step_id,
                component="semantic_action",
                expected=expected.action.to_dict(),
                actual=[candidate.to_dict() for candidate in observation.legal_actions],
            )
        selected = matches[0]
        response = environment.step(selected.candidate_id)
        actual_observation = response.observation
        actual_action = SemanticAction.from_candidate(response.applied_action)
        _expect(
            expected.step_id,
            "applied_action",
            expected.action.to_dict(),
            actual_action.to_dict(),
        )
        actual_candidate_hash = candidate_set_sha256(actual_observation.legal_actions)
        _expect(
            expected.step_id,
            "response_candidate_set_after_sha256",
            actual_candidate_hash,
            response.candidate_set_sha256,
        )
        _expect(
            expected.step_id,
            "observation_after_sha256",
            expected.observation_after_sha256,
            semantic_observation_sha256(actual_observation),
        )
        _expect(
            expected.step_id,
            "candidate_set_after_sha256",
            expected.candidate_set_after_sha256,
            actual_candidate_hash,
        )
        _expect(
            expected.step_id,
            "engine_tick_before",
            expected.engine_tick_before,
            observation.engine_tick,
        )
        _expect(
            expected.step_id,
            "engine_tick_after",
            expected.engine_tick_after,
            actual_observation.engine_tick,
        )
        actual_steps.append(
            EngineReplayStep(
                step_id=expected.step_id,
                observation_before_sha256=semantic_observation_sha256(observation),
                candidate_set_before_sha256=current_candidate_hash,
                action=actual_action,
                action_canonical_key=actual_action.canonical_key,
                recorded_candidate_id=selected.candidate_id,
                observation_after_sha256=semantic_observation_sha256(actual_observation),
                candidate_set_after_sha256=actual_candidate_hash,
                engine_tick_before=observation.engine_tick,
                engine_tick_after=actual_observation.engine_tick,
            )
        )
        observation = actual_observation

    _expect(
        replay_steps[-1].step_id,
        "final_observation_sha256",
        manifest.final_observation_sha256,
        semantic_observation_sha256(observation),
    )
    actual_trace_hash = semantic_trace_sha256(actual_steps)
    _expect(
        replay_steps[-1].step_id,
        "semantic_trace_sha256",
        manifest.semantic_trace_sha256,
        actual_trace_hash,
    )
    return actual_trace_hash


def record_engine_replay(
    environment: ReplayEnvironment,
    destination: Path,
    *,
    seed: int,
    task_id: str,
    asset_set_fingerprint: str,
    select_candidate: Callable[[Observation], int],
    max_steps: int,
) -> EngineReplayManifest:
    if max_steps <= 0:
        raise ValueError("max_steps must be positive")
    observation = environment.reset(seed=seed, task_id=task_id)
    health = environment.health
    if health is None:
        raise ValueError("recording environment did not expose a Health response")
    health.validate_compatibility(task_id)
    steps: list[EngineReplayStep] = []
    for _ in range(max_steps):
        candidate_id = select_candidate(observation)
        selected = observation.action_by_id(candidate_id)
        response = environment.step(candidate_id)
        applied = SemanticAction.from_candidate(response.applied_action)
        if applied.to_dict() != SemanticAction.from_candidate(selected).to_dict():
            raise ReplayDivergence(
                step_id=observation.step_id,
                component="applied_action",
                expected=SemanticAction.from_candidate(selected).to_dict(),
                actual=applied.to_dict(),
            )
        response_candidate_hash = candidate_set_sha256(response.observation.legal_actions)
        _expect(
            observation.step_id,
            "response_candidate_set_after_sha256",
            response_candidate_hash,
            response.candidate_set_sha256,
        )
        steps.append(
            EngineReplayStep(
                step_id=observation.step_id,
                observation_before_sha256=semantic_observation_sha256(observation),
                candidate_set_before_sha256=candidate_set_sha256(observation.legal_actions),
                action=applied,
                action_canonical_key=applied.canonical_key,
                recorded_candidate_id=candidate_id,
                observation_after_sha256=semantic_observation_sha256(response.observation),
                candidate_set_after_sha256=response_candidate_hash,
                engine_tick_before=observation.engine_tick,
                engine_tick_after=response.observation.engine_tick,
            )
        )
        observation = response.observation

    manifest = EngineReplayManifest.create(
        task_id=task_id,
        seed=seed,
        devilutionx_revision=health.devilutionx_revision,
        adapter_revision=health.adapter_revision,
        build_fingerprint=health.build_fingerprint,
        asset_set_fingerprint=asset_set_fingerprint,
        initial_observation_sha256=steps[0].observation_before_sha256,
        initial_candidate_set_sha256=steps[0].candidate_set_before_sha256,
        steps=steps,
    )
    publish_engine_replay(destination, manifest, steps)
    return manifest


def _validate_health_against_manifest(
    health: HealthResponse, manifest: EngineReplayManifest
) -> None:
    for component in (
        "adapter_revision",
        "devilutionx_revision",
        "build_fingerprint",
        "observation_version",
        "action_version",
    ):
        expected = getattr(manifest, component)
        actual = getattr(health, component)
        if actual != expected:
            raise ValueError(
                f"worker Health {component} does not match replay manifest: "
                f"expected {expected!r}, got {actual!r}"
            )
    if health.protocol_version != manifest.process_protocol_version:
        raise ValueError("worker Health protocol version does not match replay manifest")


def _expect(step_id: int, component: str, expected: object, actual: object) -> None:
    if expected != actual:
        raise ReplayDivergence(
            step_id=step_id,
            component=component,
            expected=expected,
            actual=actual,
        )
