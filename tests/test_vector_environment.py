from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from dxai.contracts.observations import Observation
from dxai.env.legal import candidate_set_sha256
from dxai.env.replay import semantic_observation_sha256
from dxai.env.vector import (
    VectorDevilutionXEnvironment,
    VectorEnvironmentCloseError,
    VectorEnvironmentError,
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


def _observations() -> tuple[Observation, Observation]:
    payload = json.loads(
        (Path(__file__).parents[1] / "schemas/examples/probe_step.example.json").read_text(
            encoding="utf-8"
        )
    )
    return Observation.from_dict(payload["observation"]), Observation.from_dict(
        payload["next_observation"]
    )


class FakeSlot:
    def __init__(
        self,
        index: int,
        root: Path,
        *,
        fail_on_step: bool = False,
        fail_on_close: bool = False,
    ) -> None:
        first, second = _observations()
        self.worker_pid = 10_000 + index
        self.runtime_root = root / f"slot-{index}"
        self.runtime_root.mkdir(parents=True)
        self._first = first
        self._second = second
        self._index = index
        self._fail_on_step = fail_on_step
        self._fail_on_close = fail_on_close
        self.observation: Observation | None = None
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
            pid=self.worker_pid,
            protocol_version=PROCESS_PROTOCOL_VERSION,
        )
        self.closed = False
        self.requests: list[int] = []

    def reset(self, *, seed: int, task_id: str) -> Observation:
        if self.closed:
            raise RuntimeError("slot is closed")
        self.observation = replace(
            self._first,
            episode_id=f"slot-{self._index}-seed-{seed}",
            seed=seed,
            task_id=task_id,
        )
        return self.observation

    def step(self, candidate_id: int) -> PersistentStepResponse:
        if self.closed:
            raise RuntimeError("slot is closed")
        if self._fail_on_step:
            raise RuntimeError("intentional slot failure")
        assert self.observation is not None
        self.requests.append(candidate_id)
        response_observation = replace(
            self._second,
            episode_id=self.observation.episode_id,
            seed=self.observation.seed,
            task_id=self.observation.task_id,
            step_id=self.observation.step_id + 1,
        )
        return_value = PersistentStepResponse(
            request_id=len(self.requests),
            episode_id=self.observation.episode_id,
            previous_step_id=self.observation.step_id,
            applied_action=self.observation.action_by_id(candidate_id),
            previous_candidate_set_sha256=candidate_set_sha256(self.observation.legal_actions),
            observation=response_observation,
            candidate_set_sha256=candidate_set_sha256(response_observation.legal_actions),
            process_state=ProcessState.EPISODE_ACTIVE,
        )
        self.observation = response_observation
        return return_value

    def close(self) -> None:
        self.closed = True
        if self._fail_on_close:
            raise RuntimeError(f"intentional close failure for slot {self._index}")


def _vector(
    tmp_path: Path,
    *,
    fail_index: int | None = None,
    fail_close_index: int | None = None,
) -> VectorDevilutionXEnvironment:
    return VectorDevilutionXEnvironment(
        2,
        environment_factory=lambda index: FakeSlot(
            index,
            tmp_path,
            fail_on_step=index == fail_index,
            fail_on_close=index == fail_close_index,
        ),
    )


def test_vector_batches_are_isolated_and_close_is_idempotent(tmp_path: Path) -> None:
    vector = _vector(tmp_path)

    observations = vector.reset_many([123, 456], "combat.single_melee.v0")
    responses = vector.step_many([0, 0])

    assert len(observations) == len(responses) == 2
    assert len(set(vector.worker_pids)) == 2
    assert len(set(vector.runtime_roots)) == 2
    assert responses[0].episode_id != responses[1].episode_id
    vector.close()
    vector.close()
    assert all(slot.closed for slot in vector.environments)


def test_vector_batch_failure_closes_every_slot(tmp_path: Path) -> None:
    vector = _vector(tmp_path, fail_index=1)
    vector.reset_many([1, 2], "combat.single_melee.v0")

    with pytest.raises(VectorEnvironmentError) as error:
        vector.step_many([0, 0])

    assert error.value.slot_index == 1
    assert all(slot.closed for slot in vector.environments)


def test_vector_close_reports_all_slot_cleanup_failures(tmp_path: Path) -> None:
    vector = _vector(tmp_path, fail_close_index=0)

    with pytest.raises(VectorEnvironmentCloseError) as error:
        vector.close()

    assert [(index, str(cause)) for index, cause in error.value.errors] == [
        (0, "intentional close failure for slot 0")
    ]
    assert all(slot.closed for slot in vector.environments)


def test_vector_batch_failure_preserves_cleanup_failure(tmp_path: Path) -> None:
    vector = _vector(tmp_path, fail_index=1, fail_close_index=0)
    vector.reset_many([1, 2], "combat.single_melee.v0")

    with pytest.raises(VectorEnvironmentError) as error:
        vector.step_many([0, 0])

    assert error.value.cleanup_error is not None
    assert error.value.cleanup_error.errors[0][0] == 0


def test_vector_rejects_wrong_batch_length(tmp_path: Path) -> None:
    vector = _vector(tmp_path)

    with pytest.raises(ValueError, match="exactly 2"):
        vector.reset_many([1], "combat.single_melee.v0")

    vector.close()


def test_vector_same_seed_matches_and_different_seed_separates_semantic_traces(
    tmp_path: Path,
) -> None:
    vector = _vector(tmp_path)

    same_seed = vector.reset_many([123, 123], "combat.single_melee.v0")
    same_hashes = [semantic_observation_sha256(item) for item in same_seed]
    different_seed = vector.reset_many([123, 456], "combat.single_melee.v0")
    different_hashes = [semantic_observation_sha256(item) for item in different_seed]

    assert len(set(same_hashes)) == 1
    assert len(set(different_hashes)) == 2
    vector.close()


def _collect_trace(
    vector: VectorDevilutionXEnvironment,
    seeds: list[int],
    steps: int,
) -> tuple[tuple[str, ...], ...]:
    observations = vector.reset_many(seeds, "combat.single_melee.v0")
    traces = [[semantic_observation_sha256(observation)] for observation in observations]
    for _ in range(steps):
        responses = vector.step_many(
            [observation.legal_actions[0].candidate_id for observation in observations]
        )
        observations = tuple(response.observation for response in responses)
        for index, observation in enumerate(observations):
            traces[index].append(semantic_observation_sha256(observation))
    return tuple(tuple(trace) for trace in traces)


def test_vector_full_trace_equality_and_seed_separation(tmp_path: Path) -> None:
    first = _vector(tmp_path / "first")
    second = _vector(tmp_path / "second")
    different = _vector(tmp_path / "different")

    same_seed_trace_a = _collect_trace(first, [123, 123], steps=2)
    same_seed_trace_b = _collect_trace(second, [123, 123], steps=2)
    different_seed_trace = _collect_trace(different, [123, 456], steps=2)

    assert same_seed_trace_a == same_seed_trace_b
    assert len(set(different_seed_trace)) == 2
    assert different_seed_trace != same_seed_trace_a

    first.close()
    second.close()
    different.close()
