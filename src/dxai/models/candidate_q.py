from __future__ import annotations

from typing import TypeAlias

import torch
from torch import Tensor, nn

HiddenState: TypeAlias = tuple[Tensor, Tensor]


class CandidateQNetwork(nn.Module):
    """Recurrent dueling Q-network over a dynamic legal candidate set.

    Shapes:
      state_features:     [batch, time, state_dim]
      candidate_features: [batch, time, candidates, candidate_dim]
      candidate_mask:     [batch, time, candidates] (True means legal/present)
    """

    def __init__(
        self,
        *,
        state_dim: int,
        candidate_dim: int,
        hidden_dim: int = 128,
        candidate_hidden_dim: int = 96,
    ) -> None:
        super().__init__()
        if min(state_dim, candidate_dim, hidden_dim, candidate_hidden_dim) <= 0:
            raise ValueError("all dimensions must be positive")
        self.state_encoder = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
        )
        self.recurrent = nn.LSTM(hidden_dim, hidden_dim, batch_first=True)
        self.candidate_encoder = nn.Sequential(
            nn.Linear(candidate_dim, candidate_hidden_dim),
            nn.LayerNorm(candidate_hidden_dim),
            nn.ReLU(),
        )
        joint_dim = hidden_dim + candidate_hidden_dim
        self.advantage = nn.Sequential(
            nn.Linear(joint_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )
        self.value = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(
        self,
        state_features: Tensor,
        candidate_features: Tensor,
        candidate_mask: Tensor,
        hidden: HiddenState | None = None,
    ) -> tuple[Tensor, HiddenState]:
        if state_features.ndim != 3:
            raise ValueError("state_features must have shape [B,T,S]")
        if candidate_features.ndim != 4:
            raise ValueError("candidate_features must have shape [B,T,A,C]")
        if candidate_mask.ndim != 3:
            raise ValueError("candidate_mask must have shape [B,T,A]")
        if candidate_features.shape[:3] != candidate_mask.shape:
            raise ValueError("candidate feature and mask dimensions differ")
        if state_features.shape[:2] != candidate_features.shape[:2]:
            raise ValueError("state and candidate batch/time dimensions differ")
        mask = candidate_mask.to(dtype=torch.bool)
        if not torch.all(mask.any(dim=-1)):
            raise ValueError("every decision must contain at least one legal candidate")

        encoded_state = self.state_encoder(state_features)
        recurrent_state, next_hidden = self.recurrent(encoded_state, hidden)
        encoded_candidate = self.candidate_encoder(candidate_features)
        expanded_state = recurrent_state.unsqueeze(2).expand(
            -1, -1, encoded_candidate.shape[2], -1
        )
        advantages = self.advantage(
            torch.cat((expanded_state, encoded_candidate), dim=-1)
        ).squeeze(-1)
        values = self.value(recurrent_state)
        mask_float = mask.to(dtype=advantages.dtype)
        mean_advantage = (advantages * mask_float).sum(dim=-1, keepdim=True) / mask_float.sum(
            dim=-1, keepdim=True
        )
        q_values = values + advantages - mean_advantage
        q_values = q_values.masked_fill(~mask, torch.finfo(q_values.dtype).min)
        return q_values, next_hidden

    @torch.no_grad()
    def greedy_actions(
        self,
        state_features: Tensor,
        candidate_features: Tensor,
        candidate_mask: Tensor,
        hidden: HiddenState | None = None,
    ) -> tuple[Tensor, HiddenState]:
        q_values, next_hidden = self.forward(
            state_features,
            candidate_features,
            candidate_mask,
            hidden,
        )
        return q_values.argmax(dim=-1), next_hidden
