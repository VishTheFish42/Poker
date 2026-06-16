"""Game table and state management for poker."""

from enum import Enum
from typing import List, Optional, Dict

from .card import Card, Deck
from .player import Player, Seat


class GameState(Enum):
    """Enumeration of game states during a hand."""
    PRE_FLOP = "pre_flop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"
    HAND_COMPLETE = "hand_complete"

    def __str__(self) -> str:
        return self.value

    @property
    def street_number(self) -> int:
        """Get the street number (0-4) for this state.
        
        Returns:
            0 for PRE_FLOP, 1 for FLOP, 2 for TURN, 3 for RIVER, 4 for SHOWDOWN
        """
        if self == GameState.PRE_FLOP:
            return 0
        elif self == GameState.FLOP:
            return 1
        elif self == GameState.TURN:
            return 2
        elif self == GameState.RIVER:
            return 3
        elif self == GameState.SHOWDOWN:
            return 4
        return -1


class Table:
    """Manages the poker table, seats, and game state."""

    MAX_PLAYERS = 10

    def __init__(self, num_seats: int = 6) -> None:
        """Initialize the poker table.

        Args:
            num_seats: Number of seats at the table (default 6, max 10)

        Raises:
            ValueError: If num_seats is invalid
        """
        if num_seats < 2 or num_seats > self.MAX_PLAYERS:
            raise ValueError(f"Table must have 2-{self.MAX_PLAYERS} seats")

        self.num_seats = num_seats
        self.seats: List[Seat] = [
            Seat(i, (360 / num_seats) * i) for i in range(num_seats)
        ]
        self.deck = Deck()
        self.community_cards: List[Card] = []
        self.game_state = GameState.PRE_FLOP
        self.current_player_seat: Optional[int] = None
        self.action_to_call = 0  # The amount to call for the current player
        self.total_pot = 0
        self.button_seat: Optional[int] = None
        self.small_blind_seat: Optional[int] = None
        self.big_blind_seat: Optional[int] = None

    def __repr__(self) -> str:
        """Return a string representation of the table."""
        occupied = sum(1 for seat in self.seats if seat.is_occupied())
        return f"Table ({occupied}/{self.num_seats} players) - {self.game_state}"

    def add_player(self, player: Player) -> None:
        """Add a player to the table.

        Args:
            player: The player to add
            
        Raises:
            ValueError: If seat is already occupied or out of range
        """
        if player.seat < 0 or player.seat >= self.num_seats:
            raise ValueError(f"Invalid seat number: {player.seat}")
        if self.seats[player.seat].is_occupied():
            raise ValueError(f"Seat {player.seat} is already occupied")
        self.seats[player.seat].set_player(player)

    def remove_player(self, seat_number: int) -> Optional[Player]:
        """Remove a player from the table.

        Args:
            seat_number: The seat number to remove from

        Returns:
            The player that was removed, or None if seat was empty
        """
        if seat_number < 0 or seat_number >= self.num_seats:
            return None
        player = self.seats[seat_number].player
        self.seats[seat_number].set_player(None)
        return player

    def get_player(self, seat_number: int) -> Optional[Player]:
        """Get the player at a specific seat.

        Args:
            seat_number: The seat number

        Returns:
            The player at that seat, or None if empty
        """
        if seat_number < 0 or seat_number >= self.num_seats:
            return None
        return self.seats[seat_number].player

    def get_active_players(self) -> List[Player]:
        """Get all active (non-folded, non-sitting-out) players.

        Returns:
            List of active players
        """
        return [
            seat.player
            for seat in self.seats
            if seat.is_occupied() and seat.player.is_active()
        ]

    def get_players_in_hand(self) -> List[Player]:
        """Get all players still in the hand (haven't folded).

        Returns:
            List of players still in the hand
        """
        return [seat.player for seat in self.seats if seat.is_occupied() and seat.player.is_active()]

    def get_all_players(self) -> List[Player]:
        """Get all players at the table.

        Returns:
            List of all seated players
        """
        return [seat.player for seat in self.seats if seat.is_occupied()]

    def reset_for_new_hand(self) -> None:
        """Reset the table for a new hand."""
        for seat in self.seats:
            if seat.is_occupied():
                seat.player.reset_for_new_hand()
        self.deck.reset()
        self.community_cards = []
        self.game_state = GameState.PRE_FLOP
        self.current_player_seat = None
        self.action_to_call = 0
        self.total_pot = 0

    def set_blinds(self, button_seat: int, small_blind_amount: int, big_blind_amount: int) -> None:
        """Set the blind positions and amounts.

        Args:
            button_seat: The seat number of the dealer button
            small_blind_amount: The small blind amount
            big_blind_amount: The big blind amount
        """
        # Clear previous blind markers
        for seat in self.seats:
            seat.clear_blind_markers()

        self.button_seat = button_seat
        self.seats[button_seat].is_button = True

        # Small blind is to the left of button
        small_blind_seat = (button_seat + 1) % self.num_seats
        self.small_blind_seat = small_blind_seat
        self.seats[small_blind_seat].is_small_blind = True

        # Big blind is to the left of small blind
        big_blind_seat = (button_seat + 2) % self.num_seats
        self.big_blind_seat = big_blind_seat
        self.seats[big_blind_seat].is_big_blind = True

    def deal_hole_cards(self) -> None:
        """Deal hole cards to all players in the hand."""
        for player in self.get_players_in_hand():
            cards = [self.deck.deal_card(), self.deck.deal_card()]
            player.receive_cards(cards)

    def deal_community_cards(self, num_cards: int) -> List[Card]:
        """Deal community cards.

        Args:
            num_cards: Number of cards to deal (3 for flop, 1 for turn/river)

        Returns:
            List of community cards dealt
        """
        dealt_cards = []
        for _ in range(num_cards):
            if not self.deck.is_empty():
                card = self.deck.deal_card()
                self.community_cards.append(card)
                dealt_cards.append(card)
        return dealt_cards

    def advance_street(self) -> GameState:
        """Advance to the next street.

        Returns:
            The new game state

        Raises:
            ValueError: If attempting to advance from SHOWDOWN or HAND_COMPLETE
        """
        if self.game_state == GameState.PRE_FLOP:
            self.game_state = GameState.FLOP
            self.deal_community_cards(3)
        elif self.game_state == GameState.FLOP:
            self.game_state = GameState.TURN
            self.deal_community_cards(1)
        elif self.game_state == GameState.TURN:
            self.game_state = GameState.RIVER
            self.deal_community_cards(1)
        elif self.game_state == GameState.RIVER:
            self.game_state = GameState.SHOWDOWN
        elif self.game_state == GameState.SHOWDOWN:
            self.game_state = GameState.HAND_COMPLETE
        else:
            raise ValueError(f"Cannot advance from {self.game_state}")

        return self.game_state

    def set_current_player(self, seat_number: int) -> None:
        """Set which player is currently acting.

        Args:
            seat_number: The seat number of the player who should act
        """
        self.current_player_seat = seat_number

    def get_next_active_player(self, from_seat: int) -> Optional[int]:
        """Get the next active player after a given seat.

        Args:
            from_seat: The seat to start looking from

        Returns:
            The seat number of the next active player, or None if no active players
        """
        for i in range(1, self.num_seats):
            seat_num = (from_seat + i) % self.num_seats
            player = self.get_player(seat_num)
            if player and player.can_act():
                return seat_num
        return None

    def get_previous_active_player(self, from_seat: int) -> Optional[int]:
        """Get the previous active player before a given seat.

        Args:
            from_seat: The seat to start looking from

        Returns:
            The seat number of the previous active player, or None if no active players
        """
        for i in range(1, self.num_seats):
            seat_num = (from_seat - i) % self.num_seats
            player = self.get_player(seat_num)
            if player and player.can_act():
                return seat_num
        return None

    def set_pot(self, amount: int) -> None:
        """Set the total pot amount.

        Args:
            amount: The new pot amount
        """
        self.total_pot = max(0, amount)

    def add_to_pot(self, amount: int) -> None:
        """Add chips to the pot.

        Args:
            amount: The amount to add
        """
        self.total_pot += max(0, amount)
