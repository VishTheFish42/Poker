"""Discrete action space for RL-controlled players (Task 5.1).

Per specs/design.md's "Action Space": Fold, Check/Call, and Bet/Raise at a
small set of sizing buckets (min, half-pot, pot) plus All-In. A policy
network (Task 5.2) only ever has to choose among `ActionSpace.size()`
discrete outputs; `ActionSpace.legal_mask()` says which are legal right
now (from `GameController.get_legal_actions()`), and
`ActionSpace.to_engine_action()` translates a chosen `AIAction` into a
real `poker.engine.action.Action` ready for `GameController.submit_action()`.
"""

from enum import Enum
from typing import Dict, List

from ..engine.action import Action, ActionType


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
    def legal_mask(legal: Dict[str, object]) -> List[bool]:
        """Build a boolean mask over `ACTIONS`, indexed by `AIAction.value`.

        Args:
            legal: A `GameController.get_legal_actions()` dict.

        Returns:
            A list of length `size()`; `mask[action.value]` is True iff
            that action is legal to submit right now.
        """
        can_open = bool(legal.get("can_bet")) or bool(legal.get("can_raise"))
        can_all_in = bool(legal.get("can_all_in"))
        can_check_or_call = bool(legal.get("can_check")) or bool(legal.get("can_call"))
        return [
            True,  # FOLD is always legal
            can_check_or_call or can_all_in,  # CHECK_CALL folds in the all-in-for-less case
            can_open,  # BET_MIN
            can_open,  # BET_HALF_POT
            can_open,  # BET_POT
            can_all_in,  # ALL_IN
        ]

    @staticmethod
    def to_engine_action(
        ai_action: AIAction, player_seat: int, legal: Dict[str, object], pot: int
    ) -> Action:
        """Translate a discrete `AIAction` into a concrete engine `Action`.

        Args:
            ai_action: The action chosen by the policy.
            player_seat: The acting player's seat.
            legal: A `GameController.get_legal_actions()` dict.
            pot: The current total pot, for the half-pot/pot sizing buckets.

        Returns:
            An `Action` ready for `GameController.submit_action()`.

        Raises:
            ValueError: If `ai_action` is not currently legal - check
                `legal_mask()` before calling this.
        """
        mask = ActionSpace.legal_mask(legal)
        if not mask[ai_action.value]:
            raise ValueError(f"{ai_action} is not legal right now: {legal}")

        if ai_action is AIAction.FOLD:
            return Action(ActionType.FOLD, player_seat)

        stack = legal["max_bet"]  # GameController always reports this as the player's stack

        if ai_action is AIAction.CHECK_CALL:
            call_amount = legal["call_amount"]
            if call_amount == 0:
                return Action(ActionType.CHECK, player_seat)
            if call_amount >= stack:
                return Action(ActionType.ALL_IN, player_seat, stack)
            return Action(ActionType.CALL, player_seat, call_amount)

        if ai_action is AIAction.ALL_IN:
            return Action(ActionType.ALL_IN, player_seat, stack)

        # The remaining actions open the betting: a BET if no wager is live
        # yet this street, otherwise a RAISE on top of one that is - never
        # both at once (GameController.get_legal_actions() guarantees this).
        opening_bet = bool(legal.get("can_bet"))
        action_type = ActionType.BET if opening_bet else ActionType.RAISE
        min_bound = legal["min_bet"] if opening_bet else legal["min_raise"]
        max_bound = legal["max_bet"] if opening_bet else legal["max_raise"]

        if ai_action is AIAction.BET_MIN:
            desired = min_bound
        elif ai_action is AIAction.BET_HALF_POT:
            desired = pot // 2
        else:  # BET_POT
            desired = pot

        amount = max(min_bound, min(desired, max_bound))
        return Action(action_type, player_seat, amount)
