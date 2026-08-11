from __future__ import annotations

import math


def signed_hyperbolic(value: float, *, epsilon: float = 1e-3) -> float:
    """R2D2-style value rescaling for large and uneven returns."""
    if not math.isfinite(value) or not math.isfinite(epsilon) or epsilon < 0:
        raise ValueError("value must be finite and epsilon must be finite and non-negative")
    return math.copysign(math.sqrt(abs(value) + 1) - 1, value) + epsilon * value


def inverse_signed_hyperbolic(value: float, *, epsilon: float = 1e-3) -> float:
    if not math.isfinite(value) or not math.isfinite(epsilon) or epsilon <= 0:
        raise ValueError("value must be finite and epsilon must be finite and positive")
    absolute = abs(value)
    inner = (math.sqrt(1 + 4 * epsilon * (absolute + 1 + epsilon)) - 1) / (2 * epsilon)
    return math.copysign(inner * inner - 1, value)


def n_step_return(
    rewards: list[float],
    *,
    bootstrap_value: float,
    gamma: float,
    terminal: bool,
) -> float:
    if not rewards:
        raise ValueError("at least one reward is required")
    if not math.isfinite(gamma) or not 0 <= gamma <= 1:
        raise ValueError("gamma must be finite and in [0, 1]")
    if not math.isfinite(bootstrap_value) or any(not math.isfinite(item) for item in rewards):
        raise ValueError("rewards and bootstrap_value must be finite")
    total = 0.0
    discount = 1.0
    for reward in rewards:
        total += discount * reward
        discount *= gamma
    if not terminal:
        total += discount * bootstrap_value
    return total
