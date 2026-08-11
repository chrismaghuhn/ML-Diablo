from __future__ import annotations

import math

from dxai.contracts.actions import ActionCandidate, ActionKind
from dxai.env.mock import DeterministicCombatEnv
from dxai.models.features import (
    FeatureSpec,
    encode_candidate,
    encode_candidates,
    encode_observation,
)


def test_reference_feature_dimensions_are_stable() -> None:
    env = DeterministicCombatEnv()
    try:
        observation = env.reset(seed=12, task_id="combat.single_melee.v0")
    finally:
        env.close()
    state = encode_observation(observation)
    candidates = encode_candidates(observation)
    assert len(state) == 16
    assert candidates
    expected = len(encode_candidate(observation.legal_actions[0], observation))
    assert expected > 10
    assert all(len(item) == expected for item in candidates)


def test_candidate_auxiliary_features_are_bounded_and_padded() -> None:
    env = DeterministicCombatEnv()
    try:
        observation = env.reset(seed=3, task_id="combat.single_melee.v0")
    finally:
        env.close()
    action = ActionCandidate(
        0,
        ActionKind.WAIT,
        features=(1.0, -1.0, 100.0),
    )
    encoded = encode_candidate(action, observation)
    spec = FeatureSpec()
    assert len(encoded) == spec.candidate_dim
    assert encoded[-8:-5] == [math.tanh(1.0), math.tanh(-1.0), math.tanh(100.0)]
    assert encoded[-5:] == [0.0] * 5
