"""Player models for the poker game engine."""

from enum import Enum
from typing import List, Optional, TYPE_CHECKING, Any

from .card import Card

if TYPE_CHECKING:
    pass  # Forward references only used in type hints


class PlayerStatus(Enum):
    """Enumeration of player statuses during a hand."""
    ACTIVE = "active"
    FOLDED = "folded"
    ALL_IN = "all_in"
    SITTING_OUT = "sitting_out"

    def __str__(self) -> str:
        return self.value


class Difficulty(Enum):
    """Enumeration of AI difficulty levels."""
    NOVICE = 1
    INTERMEDIATE = 2
    ADVANCED = 3


class Player:
    """Base class representing a player at the table."""

    def __init__(self, name: str, seat: int, initial_stack: int) -> None:
        """Initialize a player.

        Args:
            name: The player's name
            seat: The seat number (0-9)
            initial_stack: Starting chip stack
        """
        self.name = name
        self.seat = seat
        self.stack = initial_stack
        self.hole_cards: List[Card] = []
        self.status = PlayerStatus.ACTIVE
        self.current_bet = 0
        self.is_human = False

    def __repr__(self) -> str:
        """Return a string representation of the player."""
        return f"{self.name} (Seat {self.seat}) - ${self.stack}"

    def receive_cards(self, cards: List[Card]) -> None:
        """Give the player hole cards.

        Args:
            cards: List of 2 cards for the player's hand
        """
        if len(cards) != 2:
            raise ValueError("A player must receive exactly 2 hole cards.")
        self.hole_cards = cards

    def discard_cards(self) -> None:
        """Discard the player's hole cards."""
        self.hole_cards = []

    def add_chips(self, amount: int) -> None:
        """Add chips to the player's stack.

        Args:
            amount: Number of chips to add
        """
        if amount < 0:
            raise ValueError("Cannot add negative chips.")
        self.stack += amount

    def remove_chips(self, amount: int) -> int:
        """Remove chips from the player's stack (for betting/blinds).

        Args:
            amount: Number of chips to remove

        Returns:
            The actual amount removed (may be less than requested if insufficient chips)
        """
        if amount < 0:
            raise ValueError("Cannot remove negative chips.")
        actual_amount = min(amount, self.stack)
        self.stack -= actual_amount
        self.current_bet += actual_amount
        return actual_amount

    def set_current_bet(self, amount: int) -> None:
        """Set the current bet amount for this player (used for display).

        Args:
            amount: The bet amount
        """
        if amount < 0:
            raise ValueError("Current bet cannot be negative.")
        self.current_bet = amount

    def reset_for_new_hand(self) -> None:
        """Reset the player's state for a new hand."""
        self.discard_cards()
        self.status = PlayerStatus.ACTIVE if self.stack > 0 else PlayerStatus.SITTING_OUT
        self.current_bet = 0

    def fold(self) -> None:
        """Mark the player as folded."""
        self.status = PlayerStatus.FOLDED

    def go_all_in(self) -> None:
        """Mark the player as all-in."""
        self.status = PlayerStatus.ALL_IN

    def has_chips(self) -> bool:
        """Check if the player has chips remaining.

        Returns:
            True if the player has any chips, False otherwise
        """
        return self.stack > 0

    def is_active(self) -> bool:
        """Check if the player is active in the current hand.

        Returns:
            True if the player hasn't folded and isn't sitting out
        """
        return self.status in (PlayerStatus.ACTIVE, PlayerStatus.ALL_IN)

    def can_act(self) -> bool:
        """Check if the player can still take action.

        Returns:
            True if the player is active and not all-in
        """
        return self.status == PlayerStatus.ACTIVE

    def get_action(self, game_state: dict) -> "Any":
        """Get the player's action. This is meant to be overridden by subclasses.

        Args:
            game_state: Current game state information

        Raises:
            NotImplementedError: This method must be overridden in subclasses
        """
        raise NotImplementedError("Subclasses must implement get_action()")


class HumanPlayer(Player):
    """Represents a human player controlled via the UI."""

    def __init__(self, name: str, seat: int, initial_stack: int) -> None:
        """Initialize a human player.

        Args:
            name: The player's name
            seat: The seat number (0-9)
            initial_stack: Starting chip stack
        """
        super().__init__(name, seat, initial_stack)
        self.is_human = True
        self.pending_action: Optional[Any] = None
        self.action_required = False

    def set_action(self, action: "Any") -> None:
        """Set the action chosen by the human player via the UI.

        Args:
            action: The Action object representing the player's choice
        """
        self.pending_action = action
        self.action_required = False

    def is_waiting_for_action(self) -> bool:
        """Check if the player is waiting for UI input.

        Returns:
            True if the player needs to make an action choice
        """
        return self.action_required

    def get_action(self, game_state: dict) -> "Any":
        """Get the player's pending action from the UI.

        Returns:
            The Action that was set via set_action()

        Raises:
            RuntimeError: If no action has been set
        """
        if self.pending_action is None:
            raise RuntimeError(f"Player {self.name} is waiting for action but none has been set.")
        return self.pending_action


class AIPlayer(Player):
    """Represents an AI-controlled player."""

    def __init__(
        self,
        name: str,
        seat: int,
        initial_stack: int,
        difficulty: Difficulty = Difficulty.INTERMEDIATE,
    ) -> None:
        """Initialize an AI player.

        Args:
            name: The player's name
            seat: The seat number (0-9)
            initial_stack: Starting chip stack
            difficulty: The difficulty level of the AI (affects exploration)
        """
        super().__init__(name, seat, initial_stack)
        self.difficulty = difficulty
        self.ai_agent: Optional[Any] = None
        self.is_human = False

    def set_agent(self, agent: "Any") -> None:
        """Set the RL agent that controls this player's decisions.

        Args:
            agent: The RLAgent instance to use for action selection
        """
        self.ai_agent = agent

    def get_action(self, game_state: dict) -> "Any":
        """Get the player's action from the RL agent.

        Args:
            game_state: Current game state information

        Returns:
            The Action chosen by the RL agent

        Raises:
            RuntimeError: If no agent has been set
        """
        if self.ai_agent is None:
            raise RuntimeError(f"AI Player {self.name} has no agent set.")
        return self.ai_agent.select_action(game_state, self)


class Seat:
    """Represents a seat at the poker table."""

    def __init__(self, seat_number: int, position_angle: float) -> None:
        """Initialize a seat.

        Args:
            seat_number: The seat number (0-9)
            position_angle: The angle from table center (in degrees, for UI layout)
        """
        self.seat_number = seat_number
        self.position_angle = position_angle
        self.player: Optional[Player] = None
        self.is_button = False
        self.is_small_blind = False
        self.is_big_blind = False

    def __repr__(self) -> str:
        """Return a string representation of the seat."""
        if self.player:
            return f"Seat {self.seat_number}: {self.player.name}"
        return f"Seat {self.seat_number}: Empty"

    def set_player(self, player: Optional[Player]) -> None:
        """Place a player in this seat.

        Args:
            player: The player to sit, or None to empty the seat
        """
        self.player = player

    def is_occupied(self) -> bool:
        """Check if the seat has a player.

        Returns:
            True if occupied, False if empty
        """
        return self.player is not None

    def clear_blind_markers(self) -> None:
        """Clear all blind and button markers."""
        self.is_button = False
        self.is_small_blind = False
        self.is_big_blind = False

