from __future__ import annotations

import random
from dataclasses import replace

import pytest

from dxai.training.replay import (
    DualReplaySampler,
    PrioritizedSequenceReplay,
    ReplaySequence,
    ReplaySource,
    make_overlapping_sequences,
    priority_from_td_errors,
)


def test_make_overlapping_sequences(recorded_episode) -> None:
    _, _, records, _ = recorded_episode
    sequences = make_overlapping_sequences(
        records,
        source=ReplaySource.DEMONSTRATION,
        sequence_length=8,
        overlap=4,
        burn_in=3,
    )
    assert sequences
    assert all(item.source is ReplaySource.DEMONSTRATION for item in sequences)
    assert all(item.burn_in < len(item.transitions) for item in sequences)
    assert all(
        set(record.episode_id for record in item.transitions) == {records[0].episode_id}
        for item in sequences
    )


def test_priority_formula() -> None:
    assert priority_from_td_errors([1.0, -3.0], eta=1.0, epsilon=0.01) == pytest.approx(3.01)
    assert priority_from_td_errors([1.0, -3.0], eta=0.0, epsilon=0.01) == pytest.approx(2.01)


def test_prioritized_replay_sampling_and_update(recorded_episode) -> None:
    _, _, records, _ = recorded_episode
    sequences = make_overlapping_sequences(
        records,
        source=ReplaySource.AGENT,
        sequence_length=6,
        overlap=3,
        burn_in=2,
    )
    replay = PrioritizedSequenceReplay(capacity=8, alpha=0.6)
    for item in sequences:
        replay.add(item)
    assert len(replay) == len(sequences)
    replay.update_priority(sequences[0].key, 9.0)
    sample = replay.sample(16, beta=0.4, rng=random.Random(1))
    assert len(sample) == 16
    assert all(0 < item.probability <= 1 for item in sample)
    assert all(0 < item.importance_weight <= 1 for item in sample)


def test_dual_replay_respects_extreme_ratios(recorded_episode) -> None:
    _, _, records, _ = recorded_episode
    agent_item = make_overlapping_sequences(
        records, source=ReplaySource.AGENT, sequence_length=6, overlap=3, burn_in=2
    )[0]
    demo_item = replace(agent_item, key="demo", source=ReplaySource.DEMONSTRATION)
    agent = PrioritizedSequenceReplay(4)
    demos = PrioritizedSequenceReplay(4)
    agent.add(agent_item)
    demos.add(demo_item)
    sampler = DualReplaySampler(agent, demos)
    assert all(
        item.item.source is ReplaySource.AGENT
        for item in sampler.sample(10, demonstration_ratio=0, beta=0.4, rng=random.Random(2))
    )
    assert all(
        item.item.source is ReplaySource.DEMONSTRATION
        for item in sampler.sample(10, demonstration_ratio=1, beta=0.4, rng=random.Random(2))
    )


def test_sequence_rejects_episode_crossing(recorded_episode) -> None:
    _, _, records, _ = recorded_episode
    other = replace(records[1], episode_id="other")
    item = ReplaySequence(
        key="bad",
        source=ReplaySource.AGENT,
        transitions=(records[0], other),
        burn_in=1,
    )
    with pytest.raises(ValueError, match="episode boundaries"):
        item.validate()


def test_replay_rejects_non_finite_priorities_and_zero_batch(recorded_episode) -> None:
    _, _, records, _ = recorded_episode
    with pytest.raises(ValueError, match="finite"):
        priority_from_td_errors([float("nan")])
    item = make_overlapping_sequences(
        records,
        source=ReplaySource.AGENT,
        sequence_length=6,
        overlap=3,
        burn_in=2,
    )[0]
    agent = PrioritizedSequenceReplay(4)
    demos = PrioritizedSequenceReplay(4)
    agent.add(item)
    sampler = DualReplaySampler(agent, demos)
    with pytest.raises(ValueError, match="batch_size"):
        sampler.sample(0, demonstration_ratio=0, beta=0.4, rng=random.Random(1))
