"""Discrete action space for RL-controlled players (Task 5.1).

Per specs/design.md's "Action Space": Fold, Check/Call, and Bet/Raise at a
small set of sizing buckets (min, half-pot, pot) plus All-In. A policy
network (Task 5.2) only ever has to choose among `ActionSpace.size()`
discrete outputs; `ActionSpace.legal_mask()` says which are legal right
now (from the engine's `GameController.legal_actions()`), and
`ActionSpace.to_engine_action()` translates a chosen `AIAction` into a
real `poker_engine.Action` ready for `GameController.submit_action()`.
"""

from enum import Enum
from typing import List

from poker_engine import Action, ActionType, LegalActions


class AIAction(Enum):
    """The discrete choices an RL policy can output.

    Values double as the index into `ActionSpace.legal_mask()`'s result,
    so a policy network's output layer can be indexed directly by them.
    """

    FOLD = 0
    CHECK_CALL = 1
    BET_MIN = 2
    BET_HALF_POT = 3
    BET_POT = 4
    ALL_IN = 5


class ActionSpace:
    """Maps `AIAction` choices onto the engine's own `Action`/`ActionType`."""

    ACTIONS: List[AIAction] = list(AIAction)

    @staticmethod
    def size() -> int:
        """Number of discrete actions (a policy network's output width)."""
        return len(ActionSpace.ACTIONS)

    @staticmethod
    def legal_mask(legal: LegalActions) -> List[bool]:
        """Build a boolean mask over `ACTIONS`, indexed by `AIAction.value`.

        Args:
            legal: The engine's `GameController.legal_actions()`.

        Returns:
            A list of length `size()`; `mask[action.value]` is True iff
            that action is legal to submit right now.
        """
        can_open = legal.can_bet or legal.can_raise
        return [
            True,  # FOLD is always legal
            _can_check_or_call(legal),
            can_open,  # BET_MIN
            can_open,  # BET_HALF_POT
            can_open,  # BET_POT
            legal.can_all_in,  # ALL_IN
        ]

    @staticmethod
    def to_engine_action(ai_action: AIAction, legal: LegalActions, pot: int) -> Action:
        """Translate a discrete `AIAction` into a concrete engine `Action`
        for the seat on the clock (`legal.seat`).

        Args:
            ai_action: The action chosen by the policy.
            legal: The engine's `GameController.legal_actions()`.
            pot: The current total pot, for the half-pot/pot sizing buckets.

        Returns:
            An `Action` ready for `GameController.submit_action()`.

        Raises:
            ValueError: If `ai_action` is not currently legal - check
                `legal_mask()` before calling this.
        """
        mask = ActionSpace.legal_mask(legal)
        if not mask[ai_action.value]:
            raise ValueError(f"{ai_action} is not legal right now for seat {legal.seat}")

        seat = legal.seat
        if ai_action is AIAction.FOLD:
            return Action(ActionType.FOLD, seat)

        if ai_action is AIAction.CHECK_CALL:
            if legal.can_check:
                return Action(ActionType.CHECK, seat)
            if legal.can_call:
                return Action(ActionType.CALL, seat, legal.call_amount)
            # The stack can't cover the call: calling means all-in for less.
            return Action(ActionType.ALL_IN, seat, legal.all_in_amount)

        if ai_action is AIAction.ALL_IN:
            return Action(ActionType.ALL_IN, seat, legal.all_in_amount)

        # The remaining actions open the betting: a BET if no wager is live
        # yet this street, otherwise a RAISE (by an amount on top of the
        # call) - the engine never offers both at once.
        if legal.can_bet:
            action_type, min_bound, max_bound = ActionType.BET, legal.min_bet, legal.max_bet
        else:
            action_type, min_bound, max_bound = ActionType.RAISE, legal.min_raise, legal.max_raise

        if ai_action is AIAction.BET_MIN:
            desired = min_bound
        elif ai_action is AIAction.BET_HALF_POT:
            desired = pot // 2
        else:  # BET_POT
            desired = pot

        amount = max(min_bound, min(desired, max_bound))
        return Action(action_type, seat, amount)


def _can_check_or_call(legal: LegalActions) -> bool:
    """CHECK_CALL covers checking, calling, and calling all-in for less
    than the full amount owed."""
    calls_all_in_for_less = legal.can_all_in and legal.all_in_amount <= legal.call_amount
    return legal.can_check or legal.can_call or calls_all_in_for_less
