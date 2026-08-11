from __future__ import annotations

import pytest

from dxai.training.losses import inverse_signed_hyperbolic, n_step_return, signed_hyperbolic


@pytest.mark.parametrize("value", [-100.0, -1.0, 0.0, 1.0, 100.0])
def test_value_transform_is_invertible(value: float) -> None:
    assert inverse_signed_hyperbolic(signed_hyperbolic(value)) == pytest.approx(value, rel=1e-6)


def test_n_step_return_bootstraps_only_when_nonterminal() -> None:
    assert n_step_return([1.0, 2.0], bootstrap_value=4.0, gamma=0.5, terminal=False) == 3.0
    assert n_step_return([1.0, 2.0], bootstrap_value=4.0, gamma=0.5, terminal=True) == 2.0


def test_losses_reject_non_finite_inputs() -> None:
    with pytest.raises(ValueError, match="finite"):
        signed_hyperbolic(float("nan"))
    with pytest.raises(ValueError, match="finite"):
        n_step_return(
            [1.0, float("inf")],
            bootstrap_value=0.0,
            gamma=0.9,
            terminal=False,
        )
