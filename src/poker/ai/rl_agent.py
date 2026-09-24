"""RL agent for computer-controlled players (Task 5.2), with online
actor-critic training support (Task 5.4).

`RLAgent.select_action(controller, seat)` decides for the seat on the
clock of a `poker_engine.GameController`: it encodes the current state via
`ObservationEncoder`, runs it through a `PolicyNetwork`, masks out illegal
actions with `ActionSpace`, samples one, and translates it into a real
engine `Action`. `poker.ai.runner` maps seats to agents and drives hands.

Attaching a `ReplayBuffer` turns on training mode: `select_action()` then
also keeps each decision's log-probability, value estimate, and entropy
(with gradients intact) in a per-hand pending list. Once a hand ends,
`finish_hand(base_reward)` attaches that hand's terminal reward - computed
externally via `poker.ai.reward.RewardCalculator`, typically by an
`OnlineTrainer` - to every pending decision and pushes them into the
replay buffer. `update()` then drains the buffer and runs one
actor-critic step, exactly matching specs/design.md's Learning Algorithm
("policy-gradient style agent such as actor-critic... update the policy
using experience from recent hands... support online updates between
hands while the user plays") and Training Strategy ("collect experiences
from every action and store them in a replay buffer").

`save()`/`load()` (de)serialize just the policy network's weights, so a
session's training can be picked back up later (Task 5.5's "policy
persistence" - see also `poker.ai.difficulty` for tying a saved
checkpoint to a difficulty tier).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

import torch
import torch.nn.functional as F

from poker_engine import Action, Card, GameController

from .action_space import ActionSpace, AIAction
from .observation import ObservationEncoder
from .policy_network import PolicyNetwork
from .replay_buffer import Experience, ReplayBuffer
from .reward import RewardCalculator

DEFAULT_TEMPERATURE = 1.0
DEFAULT_LEARNING_RATE = 1e-3
DEFAULT_VALUE_LOSS_COEF = 0.5
DEFAULT_ENTROPY_COEF = 0.01


@dataclass
class _PendingExperience:
    """One decision awaiting this hand's terminal reward."""

    log_prob: torch.Tensor
    value: torch.Tensor
    entropy: torch.Tensor
    is_fold: bool
    hole_cards: List[Card]
    community_cards: List[Card]


class RLAgent:
    """Selects actions for one seat using a `PolicyNetwork`, optionally
    training it online from the outcomes of the hands it plays.
    """

    def __init__(
        self,
        policy: Optional[PolicyNetwork] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        deterministic: bool = False,
        generator: Optional[torch.Generator] = None,
        replay_buffer: Optional[ReplayBuffer] = None,
        learning_rate: float = DEFAULT_LEARNING_RATE,
        value_loss_coef: float = DEFAULT_VALUE_LOSS_COEF,
        entropy_coef: float = DEFAULT_ENTROPY_COEF,
    ) -> None:
        """Initialize the agent.

        Args:
            policy: The network to act with. Defaults to a fresh,
                randomly-initialized `PolicyNetwork`.
            temperature: Softmax temperature applied to masked logits
                before sampling. Higher values explore more; ignored when
                `deterministic` is True. Must be positive.
            deterministic: If True, always take the highest-probability
                legal action instead of sampling (useful for evaluation
                or a "hard" difficulty mode).
            generator: Optional `torch.Generator` for reproducible
                sampling in tests.
            replay_buffer: Attach one to enable training: `select_action()`
                will then record gradient-carrying experiences, and
                `update()` becomes usable. None (the default) means this
                agent only ever does inference.
            learning_rate: Adam learning rate, used only when training.
            value_loss_coef: Weight of the value-function loss term.
            entropy_coef: Weight of the entropy bonus (encourages
                continued exploration rather than collapsing to a single
                action too early).

        Raises:
            ValueError: If `temperature` is not positive.
        """
        if temperature <= 0:
            raise ValueError("temperature must be positive")
        self.policy = policy if policy is not None else PolicyNetwork()
        self.policy.eval()
        self.temperature = temperature
        self.deterministic = deterministic
        self.generator = generator

        self.replay_buffer = replay_buffer
        self.value_loss_coef = value_loss_coef
        self.entropy_coef = entropy_coef
        self.optimizer = (
            torch.optim.Adam(self.policy.parameters(), lr=learning_rate)
            if replay_buffer is not None
            else None
        )
        self._pending: List[_PendingExperience] = []

    @property
    def training_enabled(self) -> bool:
        """Whether this agent records experiences and can be updated."""
        return self.replay_buffer is not None

    def select_action(self, controller: GameController, seat: int) -> Action:
        """Choose and return a legal `Action` for `seat`.

        Args:
            controller: The live engine controller, with `seat` on the
                clock (`controller.current_seat == seat`).
            seat: The seat this agent is deciding for.

        Returns:
            A concrete `Action` ready for `GameController.submit_action()`.

        Raises:
            ValueError: If `seat` isn't the seat on the clock.
        """
        if controller.current_seat != seat:
            raise ValueError(f"seat {seat} is not on the clock (current seat: {controller.current_seat})")
        legal = controller.legal_actions()
        table = controller.table

        observation = ObservationEncoder.encode(controller, seat)
        # Not torch.from_numpy(): this environment's torch predates full
        # NumPy 2.x support, and that bridge crashes outright here - going
        # through a plain Python list avoids the broken C-API path.
        observation_tensor = torch.tensor(observation.tolist(), dtype=torch.float32).unsqueeze(0)

        if self.training_enabled:
            action_logits, value = self.policy(observation_tensor)
        else:
            with torch.no_grad():
                action_logits, value = self.policy(observation_tensor)

        ai_action, log_prob, entropy = self._choose(action_logits.squeeze(0), ActionSpace.legal_mask(legal))

        if self.training_enabled:
            self._pending.append(
                _PendingExperience(
                    log_prob=log_prob,
                    value=value.squeeze(0),
                    entropy=entropy,
                    is_fold=(ai_action is AIAction.FOLD),
                    hole_cards=list(table.get_player(seat).hole_cards),
                    community_cards=list(table.community_cards),
                )
            )

        return ActionSpace.to_engine_action(ai_action, legal, table.total_pot)

    def finish_hand(self, base_reward: float) -> None:
        """Attach a finished hand's terminal reward to every action this
        agent recorded during it, and push them into the replay buffer.

        A folded decision additionally gets
        `RewardCalculator.fold_strength_penalty()` on top of `base_reward`,
        using the hole/community cards visible at the moment it folded
        (captured back in `select_action()` - by the time a hand ends the
        real board may have advanced further than what this agent saw).

        A no-op if training isn't enabled, or if this agent never got to
        act this hand (e.g. it was folded/sitting out already).

        Args:
            base_reward: This hand's terminal reward from
                `RewardCalculator.for_result()`/`for_fold()`, excluding
                any fold-strength shaping (computed here instead, per action).
        """
        if not self.training_enabled:
            self._pending = []
            return

        for pending in self._pending:
            reward = base_reward
            if pending.is_fold:
                reward += RewardCalculator.fold_strength_penalty(
                    pending.hole_cards, pending.community_cards
                )
            self.replay_buffer.add(
                Experience(
                    log_prob=pending.log_prob,
                    value=pending.value,
                    entropy=pending.entropy,
                    reward=reward,
                )
            )
        self._pending = []

    def update(self) -> Optional[float]:
        """Run one actor-critic update from everything in the replay
        buffer, then clear it.

        Policy loss is `-log_prob * advantage` (advantage = reward minus
        the value estimate, so the policy is only pushed toward actions
        that did better than expected); value loss pulls the value
        estimate toward the actual reward; an entropy bonus discourages
        the policy from collapsing onto one action too early.

        Returns:
            The scalar total loss, or None if the buffer was empty.

        Raises:
            RuntimeError: If no replay buffer is attached.
        """
        if not self.training_enabled:
            raise RuntimeError("update() requires a replay_buffer to have been attached")

        experiences = self.replay_buffer.drain()
        if not experiences:
            return None

        log_probs = torch.stack([exp.log_prob for exp in experiences])
        values = torch.stack([exp.value for exp in experiences])
        entropies = torch.stack([exp.entropy for exp in experiences])
        rewards = torch.tensor([exp.reward for exp in experiences], dtype=torch.float32)

        advantages = rewards - values.detach()
        policy_loss = -(log_probs * advantages).mean()
        value_loss = F.mse_loss(values, rewards)
        entropy_bonus = entropies.mean()
        loss = policy_loss + self.value_loss_coef * value_loss - self.entropy_coef * entropy_bonus

        self.policy.train()
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        self.policy.eval()

        return float(loss.item())

    def save(self, path: Union[str, Path]) -> None:
        """Save this agent's policy network weights to `path`.

        Only the network weights are persisted - not the replay buffer,
        optimizer state, or any other in-progress training state - so a
        loaded agent always starts training fresh even if the original
        session was mid-update.

        Args:
            path: File to write the checkpoint to. Parent directories are
                created if needed.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.policy.state_dict(), path)

    @classmethod
    def load(cls, path: Union[str, Path], **kwargs: object) -> "RLAgent":
        """Build an `RLAgent` whose policy network is restored from `path`.

        Args:
            path: A checkpoint file previously written by `save()`.
            **kwargs: Forwarded to `RLAgent.__init__` (e.g. `temperature`,
                `deterministic`, `replay_buffer`).

        Returns:
            A new `RLAgent` using the restored network.

        Raises:
            FileNotFoundError: If `path` does not exist.
        """
        policy = PolicyNetwork()
        state_dict = torch.load(Path(path), map_location="cpu")
        policy.load_state_dict(state_dict)
        return cls(policy=policy, **kwargs)

    def _choose(self, logits: torch.Tensor, mask: list) -> tuple:
        """Mask illegal actions out of `logits`, then pick one.

        Returns:
            A `(AIAction, log_prob, entropy)` tuple - the log-probability
            and entropy are of the full masked distribution, kept as
            tensors so `select_action()` can retain their gradients.
        """
        masked_logits = logits.clone()
        for index, is_legal in enumerate(mask):
            if not is_legal:
                masked_logits[index] = float("-inf")

        probabilities = torch.softmax(masked_logits / self.temperature, dim=-1)

        if self.deterministic:
            chosen_index = int(torch.argmax(masked_logits).item())
        else:
            chosen_index = int(
                torch.multinomial(probabilities, num_samples=1, generator=self.generator).item()
            )

        log_prob = torch.log(probabilities[chosen_index] + 1e-8)
        entropy = -(probabilities * torch.log(probabilities + 1e-8)).sum()

        return ActionSpace.ACTIONS[chosen_index], log_prob, entropy
