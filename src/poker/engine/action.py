"""Action types and handling for the poker game."""

from enum import Enum
from typing import Optional


class ActionType(Enum):
    """Enumeration of possible player actions."""
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"

    def __str__(self) -> str:
        return self.value


class Action:
    """Represents a player action in the game."""

    def __init__(self, action_type: ActionType, player_seat: int, amount: int = 0) -> None:
        """Initialize an action.

        Args:
            action_type: The type of action (fold, check, call, bet, raise, all_in)
            player_seat: The seat number of the player taking the action
            amount: The amount of chips (for bet/raise/call/all_in, 0 for check/fold)

        Raises:
            ValueError: If action parameters are invalid
        """
        self.action_type = action_type
        self.player_seat = player_seat
        self.amount = amount

        # Validate action parameters
        if action_type in (ActionType.FOLD, ActionType.CHECK) and amount != 0:
            raise ValueError(f"{action_type} actions must have amount=0")
        if action_type in (ActionType.BET, ActionType.RAISE, ActionType.CALL, ActionType.ALL_IN):
            if amount < 0:
                raise ValueError(f"{action_type} amount cannot be negative")

    def __repr__(self) -> str:
        """Return a string representation of the action."""
        if self.amount > 0:
            return f"Seat {self.player_seat}: {self.action_type} ${self.amount}"
        return f"Seat {self.player_seat}: {self.action_type}"

    def __eq__(self, other: object) -> bool:
        """Check if two actions are equal."""
        if not isinstance(other, Action):
            return NotImplemented
        return (
            self.action_type == other.action_type
            and self.player_seat == other.player_seat
            and self.amount == other.amount
        )
