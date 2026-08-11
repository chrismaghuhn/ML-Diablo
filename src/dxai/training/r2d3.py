from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class R2D3Config:
    """Evidence-based starting point, not a claim of tuned Diablo hyperparameters."""

    gamma: float = 0.997
    n_step: int = 5
    sequence_length: int = 80
    burn_in: int = 40
    sequence_overlap: int = 40
    batch_size: int = 64
    replay_capacity_sequences: int = 100_000
    demonstration_capacity_sequences: int = 20_000
    demonstration_ratio: float = 1 / 128
    replay_alpha: float = 0.6
    importance_beta_start: float = 0.4
    importance_beta_end: float = 1.0
    priority_eta: float = 0.9
    target_update_steps: int = 2_500
    learning_rate: float = 2e-4
    actor_count: int = 8
    actor_epsilon_base: float = 0.4
    actor_epsilon_exponent: float = 8.0
    gradient_clip_norm: float = 40.0

    def validate(self) -> None:
        if not math.isfinite(self.gamma) or not 0 < self.gamma <= 1:
            raise ValueError("gamma must be finite and in (0, 1]")
        positive_integers = (
            self.n_step,
            self.sequence_length,
            self.batch_size,
            self.replay_capacity_sequences,
            self.demonstration_capacity_sequences,
            self.target_update_steps,
            self.actor_count,
        )
        if any(value <= 0 for value in positive_integers):
            raise ValueError("integer capacities, lengths and counts must be positive")
        if not 0 < self.burn_in < self.sequence_length:
            raise ValueError("burn_in must be inside the sequence")
        if not 0 <= self.sequence_overlap < self.sequence_length:
            raise ValueError("invalid sequence overlap")
        if not 0 <= self.demonstration_ratio <= 1:
            raise ValueError("demonstration_ratio must be in [0, 1]")
        if not 0 <= self.replay_alpha <= 1:
            raise ValueError("replay_alpha must be in [0, 1]")
        if not (
            0 <= self.importance_beta_start <= self.importance_beta_end <= 1
        ):
            raise ValueError("importance beta schedule must be ordered inside [0, 1]")
        if not 0 <= self.priority_eta <= 1:
            raise ValueError("priority_eta must be in [0, 1]")
        positive_floats = (
            self.learning_rate,
            self.actor_epsilon_base,
            self.actor_epsilon_exponent,
            self.gradient_clip_norm,
        )
        if any(not math.isfinite(value) or value <= 0 for value in positive_floats):
            raise ValueError("learning and actor scalar parameters must be finite and positive")
        if self.actor_epsilon_base > 1:
            raise ValueError("actor_epsilon_base must not exceed one")

    @property
    def learning_length(self) -> int:
        return self.sequence_length - self.burn_in

    def actor_epsilons(self) -> tuple[float, ...]:
        self.validate()
        if self.actor_count == 1:
            return (self.actor_epsilon_base**self.actor_epsilon_exponent,)
        return tuple(
            self.actor_epsilon_base
            ** (1 + (self.actor_epsilon_exponent - 1) * index / (self.actor_count - 1))
            for index in range(self.actor_count)
        )
