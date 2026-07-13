"""Reward signals for RL-controlled players (Task 5.3).

Per specs/design.md's "Reward Structure": rewards are built from the
final chip gain/loss for a hand, plus shaping terms for preserving chips
and winning pots, plus penalties for folding an already-strong hand or
calling all the way to a losing showdown with a weak one. Amounts are
expressed in big blinds, matching `poker.ai.observation.ObservationEncoder`,
so the same reward scale generalizes across stake levels.

Two entry points cover the two ways a hand can end for a given player:
`for_result()` for anyone present in a `ShowdownResult` (they reached
showdown or won an uncontested pot), and `for_fold()` for anyone who
folded before that (and so never appears in `ShowdownResult` at all).
"""

from typing import List, Optional

from ..engine.card import Card
from ..engine.hand_evaluator import HandEvaluator, HandType
from ..engine.showdown import PlayerResult

WIN_BONUS = 0.5
BUST_PENALTY = -1.0
STRONG_FOLD_THRESHOLD = HandType.TWO_PAIR
STRONG_FOLD_PENALTY = -0.5
WEAK_SHOWDOWN_THRESHOLD = HandType.ONE_PAIR
WEAK_SHOWDOWN_LOSS_PENALTY = -0.25


class RewardCalculator:
    """Computes a scalar reward for one player's outcome in a single hand."""

    @staticmethod
    def for_result(
        player_result: PlayerResult,
        contribution: int,
        stack_after: int,
        big_blind: int,
        is_showdown: bool,
    ) -> float:
        """Reward for a player present in a hand's `ShowdownResult` - they
        reached showdown or won an uncontested pot (did not fold).

        Args:
            player_result: This player's entry in `ShowdownResult.player_results`.
            contribution: Total chips this player put into the pot this hand.
            stack_after: This player's stack once winnings are credited.
            big_blind: The hand's big blind amount, for scaling to a
                stake-independent reward.
            is_showdown: Whether 2+ players compared hands (False for an
                uncontested fold-win, where losing at showdown can't apply).

        Returns:
            The reward, in big blinds.
        """
        big_blind = max(big_blind, 1)
        reward = (player_result.chips_won - contribution) / big_blind

        if player_result.chips_won > 0:
            reward += WIN_BONUS
        elif is_showdown and player_result.best_hand is not None:
            if player_result.best_hand.hand_type < WEAK_SHOWDOWN_THRESHOLD:
                reward += WEAK_SHOWDOWN_LOSS_PENALTY

        if stack_after <= 0:
            reward += BUST_PENALTY

        return reward

    @staticmethod
    def for_fold(
        contribution: int,
        stack_after: int,
        big_blind: int,
        hole_cards: Optional[List[Card]] = None,
        community_cards: Optional[List[Card]] = None,
    ) -> float:
        """Reward for a player who folded this hand (never appears in the
        hand's `ShowdownResult`).

        Args:
            contribution: Total chips this player put into the pot before folding.
            stack_after: This player's stack after folding (unaffected by
                this hand's pot, but may already be 0 from a prior hand).
            big_blind: The hand's big blind amount, for scaling.
            hole_cards: This player's hole cards, if scoring the fold's
                strength penalty (see `fold_strength_penalty`).
            community_cards: The community cards visible at the moment of
                the fold (not the final board - the player never saw that).

        Returns:
            The reward, in big blinds.
        """
        big_blind = max(big_blind, 1)
        reward = -contribution / big_blind
        reward += RewardCalculator.fold_strength_penalty(hole_cards, community_cards)

        if stack_after <= 0:
            reward += BUST_PENALTY

        return reward

    @staticmethod
    def fold_strength_penalty(
        hole_cards: Optional[List[Card]], community_cards: Optional[List[Card]]
    ) -> float:
        """Shaping penalty for folding an already-made strong hand (two
        pair or better).

        Only scoreable when exactly 5 cards are known (2 hole + a 3-card
        flop) - `HandEvaluator.evaluate_hand` requires exactly 5 cards, and
        the engine has no partial-board evaluator for the 2 (preflop) or 6
        (turn) card cases. Those return 0 rather than approximating -
        extending `HandEvaluator` to score partial boards is out of this
        task's scope.

        Args:
            hole_cards: The folding player's hole cards.
            community_cards: The community cards visible when they folded.

        Returns:
            `STRONG_FOLD_PENALTY` if the folded hand was two pair or
            better, otherwise 0.0.
        """
        cards = list(hole_cards or []) + list(community_cards or [])
        if len(cards) != 5:
            return 0.0

        hand = HandEvaluator.evaluate_hand(cards)
        if hand.hand_type >= STRONG_FOLD_THRESHOLD:
            return STRONG_FOLD_PENALTY
        return 0.0
