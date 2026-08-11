from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from dxai.models.candidate_q import CandidateQNetwork  # noqa: E402


def test_candidate_q_shapes_and_mask() -> None:
    torch.manual_seed(1)
    model = CandidateQNetwork(state_dim=16, candidate_dim=27, hidden_dim=32)
    states = torch.randn(2, 5, 16)
    candidates = torch.randn(2, 5, 7, 27)
    mask = torch.ones(2, 5, 7, dtype=torch.bool)
    mask[:, :, -2:] = False
    q_values, hidden = model(states, candidates, mask)
    assert q_values.shape == (2, 5, 7)
    assert hidden[0].shape == (1, 2, 32)
    assert torch.isfinite(q_values[:, :, :5]).all()
    assert (q_values[:, :, -2:] == torch.finfo(q_values.dtype).min).all()


def test_candidate_permutation_equivariance() -> None:
    torch.manual_seed(2)
    model = CandidateQNetwork(state_dim=4, candidate_dim=3, hidden_dim=16)
    model.eval()
    states = torch.randn(1, 2, 4)
    candidates = torch.randn(1, 2, 5, 3)
    mask = torch.ones(1, 2, 5, dtype=torch.bool)
    permutation = torch.tensor([3, 0, 4, 1, 2])
    original, _ = model(states, candidates, mask)
    permuted, _ = model(states, candidates[:, :, permutation], mask[:, :, permutation])
    inverse = torch.argsort(permutation)
    assert torch.allclose(original, permuted[:, :, inverse], atol=1e-6)


def test_all_invalid_candidates_are_rejected() -> None:
    model = CandidateQNetwork(state_dim=4, candidate_dim=3, hidden_dim=8)
    with pytest.raises(ValueError, match="at least one"):
        model(
            torch.zeros(1, 1, 4),
            torch.zeros(1, 1, 2, 3),
            torch.zeros(1, 1, 2, dtype=torch.bool),
        )
