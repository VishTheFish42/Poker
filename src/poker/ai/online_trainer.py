"""Online training loop wiring hand outcomes into RLAgent updates (Task 5.4).

Per specs/design.md's Training Strategy ("periodically update the policy
after a small batch of hands") and Data Flow ("training feedback is
emitted asynchronously to avoid blocking the UI"): after each hand
completes, `OnlineTrainer.process_completed_hand()` computes every
training-enabled AI seat's terminal reward from the engine's
`GameController.last_result` via `RewardCalculator`, hands it to that
seat's `RLAgent.finish_hand()`, and - every `hands_per_update` hands -
triggers `RLAgent.update()`. It never touches betting/dealing itself, so
calling it is a single extra line wherever a hand loop already lives (a
script, the eventual UI hand-completion hook, or a test).
"""

from typing import Dict, Mapping

from poker_engine import GameController

from .reward import RewardCalculator
from .rl_agent import RLAgent


class OnlineTrainer:
    """Feeds finished hands' outcomes into each AI seat's `RLAgent`."""

    def __init__(self, hands_per_update: int = 1) -> None:
        """Initialize the trainer.

        Args:
            hands_per_update: How many completed hands to accumulate
                before triggering a policy update (a "small batch of
                hands", per specs/design.md). Coerced to at least 1.
        """
        self.hands_per_update = max(hands_per_update, 1)
        self._hands_since_update = 0

    def process_completed_hand(
        self, controller: GameController, agents: Mapping[int, RLAgent]
    ) -> Dict[int, float]:
        """Record this hand's outcome for every training-enabled AI seat.

        Args:
            controller: The controller whose hand just finished (i.e.
                `controller.is_hand_complete` is True and
                `controller.last_result` is set).
            agents: `{seat: agent}` for the AI seats at this table. Seats
                without an agent (e.g. a human) are ignored.

        Returns:
            A mapping of seat -> reward for every seat whose agent is
            training-enabled (useful for logging; empty if
            `controller.last_result` is unset).
        """
        result = controller.last_result
        if result is None:
            return {}

        table = controller.table
        contributions = controller.contributions
        result_by_seat = {r.seat: r for r in result.player_results}
        big_blind = controller.big_blind_amount
        rewards: Dict[int, float] = {}

        for seat, agent in agents.items():
            player = table.get_player(seat)
            if player is None or not agent.training_enabled:
                continue

            contribution = contributions.get(seat, 0)
            player_result = result_by_seat.get(seat)

            if player_result is not None:
                reward = RewardCalculator.for_result(
                    player_result, contribution, player.stack, big_blind, result.is_showdown
                )
            else:
                # Not in the result at all means this seat folded (or sat
                # out) before showdown; the fold-strength shaping term is
                # added inside finish_hand() itself, from cards captured at
                # fold time.
                reward = RewardCalculator.for_fold(contribution, player.stack, big_blind)

            agent.finish_hand(reward)
            rewards[seat] = reward

        self._hands_since_update += 1
        if self._hands_since_update >= self.hands_per_update:
            for agent in agents.values():
                if agent.training_enabled:
                    agent.update()
            self._hands_since_update = 0

        return rewards
