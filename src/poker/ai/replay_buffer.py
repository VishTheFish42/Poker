"""Experience storage for RLAgent's online policy updates (Task 5.4).

Each `Experience` is one action `RLAgent` took while training was
enabled: the log-probability, value estimate, and entropy the policy
network produced for it (all still attached to the network's autograd
graph), plus the scalar reward its hand eventually earned. `RLAgent.update()`
drains a buffer and backpropagates through exactly these tensors - no
recomputation of the forward pass is needed.
"""

from dataclasses import dataclass
from typing import List, Optional

import torch


@dataclass
class Experience:
    """One recorded decision, ready for a policy update."""

    log_prob: torch.Tensor
    value: torch.Tensor
    entropy: torch.Tensor
    reward: float


class ReplayBuffer:
    """An in-order buffer of `Experience`s awaiting a policy update."""

    def __init__(self, capacity: Optional[int] = None) -> None:
        """Initialize the buffer.

        Args:
            capacity: Maximum experiences to hold at once. When full, the
                oldest experience is dropped to make room for a new one.
                None means unbounded.
        """
        self.capacity = capacity
        self._experiences: List[Experience] = []

    def add(self, experience: Experience) -> None:
        """Append `experience`, evicting the oldest one if at capacity."""
        self._experiences.append(experience)
        if self.capacity is not None and len(self._experiences) > self.capacity:
            self._experiences.pop(0)

    def drain(self) -> List[Experience]:
        """Return all stored experiences and clear the buffer."""
        experiences = self._experiences
        self._experiences = []
        return experiences

    def __len__(self) -> int:
        return len(self._experiences)
