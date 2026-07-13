"""Policy network for RL-controlled players (Task 5.2).

A small actor-critic MLP: a shared trunk feeds a policy head (one logit
per `ActionSpace` action) and a value head (a scalar estimate of the
position's worth). The policy head is what `RLAgent` samples actions
from; the value head only matters once Task 5.4 wires up an actual
training loop - `RLAgent` on its own just ignores it.
"""

from typing import Optional, Sequence, Tuple

import torch
from torch import nn

from .action_space import ActionSpace
from .observation import ObservationEncoder

DEFAULT_HIDDEN_SIZES = (128, 128)


class PolicyNetwork(nn.Module):
    """Maps an encoded observation to action logits and a value estimate."""

    def __init__(
        self,
        observation_size: Optional[int] = None,
        action_size: Optional[int] = None,
        hidden_sizes: Sequence[int] = DEFAULT_HIDDEN_SIZES,
    ) -> None:
        """Initialize the network.

        Args:
            observation_size: Input feature count. Defaults to
                `ObservationEncoder.size()`.
            action_size: Number of discrete actions. Defaults to
                `ActionSpace.size()`.
            hidden_sizes: Width of each shared hidden layer.
        """
        super().__init__()
        observation_size = observation_size or ObservationEncoder.size()
        action_size = action_size or ActionSpace.size()

        layers = []
        in_size = observation_size
        for hidden_size in hidden_sizes:
            layers.append(nn.Linear(in_size, hidden_size))
            layers.append(nn.ReLU())
            in_size = hidden_size
        self.trunk = nn.Sequential(*layers)

        self.policy_head = nn.Linear(in_size, action_size)
        self.value_head = nn.Linear(in_size, 1)

    def forward(self, observation: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Compute action logits and a value estimate for a batch of observations.

        Args:
            observation: Float tensor of shape `(batch, observation_size)`.

        Returns:
            A `(action_logits, value)` pair: logits of shape
            `(batch, action_size)` and value of shape `(batch,)`.
        """
        hidden = self.trunk(observation)
        action_logits = self.policy_head(hidden)
        value = self.value_head(hidden).squeeze(-1)
        return action_logits, value
