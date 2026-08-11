from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import StrEnum

from dxai.data.trajectory import TransitionRecord


class ReplaySource(StrEnum):
    AGENT = "AGENT"
    DEMONSTRATION = "DEMONSTRATION"


@dataclass(frozen=True, slots=True)
class ReplaySequence:
    key: str
    source: ReplaySource
    transitions: tuple[TransitionRecord, ...]
    burn_in: int
    priority: float = 1.0

    def validate(self) -> None:
        if not self.key or not self.transitions:
            raise ValueError("replay sequence needs a key and transitions")
        if self.priority <= 0 or not math.isfinite(self.priority):
            raise ValueError("priority must be finite and positive")
        if not 0 <= self.burn_in < len(self.transitions):
            raise ValueError("burn_in must leave at least one learning transition")
        episode_ids = {item.episode_id for item in self.transitions}
        task_ids = {item.task_id for item in self.transitions}
        seeds = {item.seed for item in self.transitions}
        if len(episode_ids) != 1:
            raise ValueError("a replay sequence may not cross episode boundaries")
        if len(task_ids) != 1 or len(seeds) != 1:
            raise ValueError("a replay sequence must keep task and seed constant")
        if any(item.terminated or item.truncated for item in self.transitions[:-1]):
            raise ValueError("a replay sequence may not continue past a terminal boundary")
        for transition in self.transitions:
            transition.validate()
        expected = list(
            range(
                self.transitions[0].step_id,
                self.transitions[0].step_id + len(self.transitions),
            )
        )
        actual = [item.step_id for item in self.transitions]
        if actual != expected:
            raise ValueError("replay transitions must be contiguous")


@dataclass(frozen=True, slots=True)
class SampledSequence:
    item: ReplaySequence
    probability: float
    importance_weight: float


class PrioritizedSequenceReplay:
    """Small reference implementation for contract tests and local experiments.

    This O(N) sampler is intentionally simple. Replace it with a segment tree or a
    replay service once profiling proves that replay is the bottleneck.
    """

    def __init__(self, capacity: int, *, alpha: float = 0.6) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if not 0 <= alpha <= 1:
            raise ValueError("alpha must be in [0, 1]")
        self.capacity = capacity
        self.alpha = alpha
        self._items: list[ReplaySequence] = []
        self._by_key: dict[str, int] = {}

    def __len__(self) -> int:
        return len(self._items)

    def add(self, item: ReplaySequence) -> None:
        item.validate()
        if item.key in self._by_key:
            index = self._by_key[item.key]
            self._items[index] = item
            return
        if len(self._items) >= self.capacity:
            removed = self._items.pop(0)
            del self._by_key[removed.key]
            self._by_key = {stored.key: index for index, stored in enumerate(self._items)}
        self._by_key[item.key] = len(self._items)
        self._items.append(item)

    def update_priority(self, key: str, priority: float) -> None:
        if priority <= 0 or not math.isfinite(priority):
            raise ValueError("priority must be finite and positive")
        try:
            index = self._by_key[key]
        except KeyError as error:
            raise KeyError(f"unknown replay key {key!r}") from error
        old = self._items[index]
        self._items[index] = ReplaySequence(
            key=old.key,
            source=old.source,
            transitions=old.transitions,
            burn_in=old.burn_in,
            priority=priority,
        )

    def sample(self, batch_size: int, *, beta: float, rng: random.Random) -> list[SampledSequence]:
        if not self._items:
            raise ValueError("cannot sample an empty replay")
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if not 0 <= beta <= 1:
            raise ValueError("beta must be in [0, 1]")
        weights = [item.priority**self.alpha for item in self._items]
        total = sum(weights)
        probabilities = [weight / total for weight in weights]
        indices = rng.choices(range(len(self._items)), weights=weights, k=batch_size)
        raw_importance = [
            (len(self._items) * probabilities[index]) ** (-beta) for index in indices
        ]
        normalizer = max(raw_importance)
        return [
            SampledSequence(
                item=self._items[index],
                probability=probabilities[index],
                importance_weight=raw / normalizer,
            )
            for index, raw in zip(indices, raw_importance, strict=True)
        ]


class DualReplaySampler:
    """Stochastically mixes independent demonstration and agent replay buffers."""

    def __init__(
        self,
        agent_replay: PrioritizedSequenceReplay,
        demonstration_replay: PrioritizedSequenceReplay,
    ) -> None:
        self.agent_replay = agent_replay
        self.demonstration_replay = demonstration_replay

    def sample(
        self,
        batch_size: int,
        *,
        demonstration_ratio: float,
        beta: float,
        rng: random.Random,
    ) -> list[SampledSequence]:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if not 0 <= demonstration_ratio <= 1:
            raise ValueError("demonstration_ratio must be in [0, 1]")
        if not self.agent_replay and not self.demonstration_replay:
            raise ValueError("both replay buffers are empty")
        result: list[SampledSequence] = []
        for _ in range(batch_size):
            use_demo = rng.random() < demonstration_ratio
            if use_demo and self.demonstration_replay:
                result.extend(self.demonstration_replay.sample(1, beta=beta, rng=rng))
            elif self.agent_replay:
                result.extend(self.agent_replay.sample(1, beta=beta, rng=rng))
            else:
                result.extend(self.demonstration_replay.sample(1, beta=beta, rng=rng))
        return result


def make_overlapping_sequences(
    transitions: list[TransitionRecord],
    *,
    source: ReplaySource,
    sequence_length: int,
    overlap: int,
    burn_in: int,
    initial_priority: float = 1.0,
) -> list[ReplaySequence]:
    if not transitions:
        return []
    if sequence_length <= 0:
        raise ValueError("sequence_length must be positive")
    if not 0 <= overlap < sequence_length:
        raise ValueError("overlap must be in [0, sequence_length)")
    if burn_in < 0 or burn_in >= sequence_length:
        raise ValueError("burn_in must be in [0, sequence_length)")
    if initial_priority <= 0 or not math.isfinite(initial_priority):
        raise ValueError("initial_priority must be finite and positive")
    stride = sequence_length - overlap
    result: list[ReplaySequence] = []
    for start in range(0, len(transitions), stride):
        chunk = transitions[start : start + sequence_length]
        if len(chunk) <= burn_in:
            break
        item = ReplaySequence(
            key=f"{chunk[0].episode_id}:{chunk[0].step_id}:{len(chunk)}:{source.value}",
            source=source,
            transitions=tuple(chunk),
            burn_in=min(burn_in, len(chunk) - 1),
            priority=initial_priority,
        )
        item.validate()
        result.append(item)
        if start + sequence_length >= len(transitions):
            break
    return result


def priority_from_td_errors(
    errors: list[float],
    *,
    eta: float = 0.9,
    epsilon: float = 1e-3,
) -> float:
    if not errors:
        raise ValueError("TD errors are required")
    if not 0 <= eta <= 1 or epsilon <= 0:
        raise ValueError("invalid priority parameters")
    if any(not math.isfinite(value) for value in errors):
        raise ValueError("TD errors must be finite")
    absolute = [abs(value) for value in errors]
    return eta * max(absolute) + (1 - eta) * (sum(absolute) / len(absolute)) + epsilon
