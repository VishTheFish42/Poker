"""Betting round management for poker."""

from typing import List, Optional, Dict, Tuple
from .action import Action, ActionType
from .player import Player, PlayerStatus
from .table import Table


class BettingRound:
    """Manages the betting for a single street."""

    def __init__(
        self,
        table: Table,
        small_blind_amount: int,
        big_blind_amount: int,
        start_seat: int,
    ) -> None:
        """Initialize a betting round.

        Args:
            table: The Table object managing the game
            small_blind_amount: The small blind amount
            big_blind_amount: The big blind amount
            start_seat: The seat number to start betting from (UTG on pre-flop, SB after)
        """
        self.table = table
        self.small_blind_amount = small_blind_amount
        self.big_blind_amount = big_blind_amount
        self.start_seat = start_seat
        self.actions: List[Action] = []
        self.player_bet_amounts: Dict[int, int] = {}  # Seat -> Total bet this round
        self.round_complete = False
        self.current_bettor_seat: Optional[int] = None
        self.highest_bet = 0  # Highest bet/raise amount this round
        self.players_acted: int = 0
        self.min_raise_amount = big_blind_amount  # Minimum raise amount

    def __repr__(self) -> str:
        """Return a string representation of the betting round."""
        return f"BettingRound: {len(self.actions)} actions, pot ${self.table.total_pot}"

    def initialize_blinds(self) -> None:
        """Post the blind amounts."""
        # Post small blind
        if self.table.small_blind_seat is not None:
            sb_player = self.table.get_player(self.table.small_blind_seat)
            if sb_player:
                amount = min(self.small_blind_amount, sb_player.stack)
                actual = sb_player.remove_chips(amount)
                self.player_bet_amounts[self.table.small_blind_seat] = actual
                self.table.add_to_pot(actual)
                self.highest_bet = actual

        # Post big blind
        if self.table.big_blind_seat is not None:
            bb_player = self.table.get_player(self.table.big_blind_seat)
            if bb_player:
                amount = min(self.big_blind_amount, bb_player.stack)
                actual = bb_player.remove_chips(amount)
                self.player_bet_amounts[self.table.big_blind_seat] = actual
                self.table.add_to_pot(actual)
                self.highest_bet = max(self.highest_bet, actual)
                self.min_raise_amount = actual

    def get_amount_to_call(self, seat_number: int) -> int:
        """Get the amount a player needs to call to stay in the hand.

        Args:
            seat_number: The player's seat number

        Returns:
            The amount the player needs to add to call (call amount - already bet)
        """
        current_bet = self.player_bet_amounts.get(seat_number, 0)
        return max(0, self.highest_bet - current_bet)

    def can_check(self, seat_number: int) -> bool:
        """Check if a player can check (amount to call is 0).

        Args:
            seat_number: The player's seat number

        Returns:
            True if the player can check
        """
        return self.get_amount_to_call(seat_number) == 0

    def process_action(self, action: Action) -> bool:
        """Process a player action.

        Args:
            action: The Action to process

        Returns:
            True if the action was valid, False otherwise

        Raises:
            ValueError: If the action is invalid
        """
        player = self.table.get_player(action.player_seat)
        if not player:
            raise ValueError(f"No player in seat {action.player_seat}")

        amount_to_call = self.get_amount_to_call(action.player_seat)

        # Validate the action
        if action.action_type == ActionType.CHECK:
            if amount_to_call > 0:
                raise ValueError(f"Cannot check with ${amount_to_call} to call")
        elif action.action_type == ActionType.FOLD:
            pass  # Always valid
        elif action.action_type == ActionType.CALL:
            if amount_to_call > player.stack:
                raise ValueError(
                    f"Cannot call ${amount_to_call} with stack of ${player.stack}"
                )
        elif action.action_type == ActionType.BET:
            if amount_to_call > 0:
                raise ValueError(
                    f"Cannot bet when there's ${amount_to_call} to call (must call or raise)"
                )
            if action.amount > player.stack:
                raise ValueError(f"Cannot bet ${action.amount} with stack of ${player.stack}")
        elif action.action_type == ActionType.RAISE:
            total_call_and_raise = amount_to_call + action.amount
            if total_call_and_raise > player.stack:
                raise ValueError(
                    f"Cannot raise ${action.amount} with only ${player.stack} remaining"
                )
            if action.amount < self.min_raise_amount:
                raise ValueError(
                    f"Raise of ${action.amount} is less than min raise of ${self.min_raise_amount}"
                )
        elif action.action_type == ActionType.ALL_IN:
            pass  # Always valid (player bets/calls remaining stack)

        # Execute the action
        self.actions.append(action)
        self.players_acted += 1
        self.table.set_current_player(action.player_seat)

        if action.action_type == ActionType.FOLD:
            player.fold()
        elif action.action_type == ActionType.CHECK:
            # No chips added
            pass
        elif action.action_type == ActionType.CALL:
            chips_added = player.remove_chips(amount_to_call)
            self.player_bet_amounts[action.player_seat] = (
                self.player_bet_amounts.get(action.player_seat, 0) + chips_added
            )
            self.table.add_to_pot(chips_added)
        elif action.action_type == ActionType.BET:
            chips_added = player.remove_chips(action.amount)
            self.player_bet_amounts[action.player_seat] = (
                self.player_bet_amounts.get(action.player_seat, 0) + chips_added
            )
            self.table.add_to_pot(chips_added)
            self.highest_bet = max(self.highest_bet, chips_added)
            self.min_raise_amount = chips_added
        elif action.action_type == ActionType.RAISE:
            call_amount = player.remove_chips(amount_to_call)
            raise_amount = player.remove_chips(action.amount)
            total_added = call_amount + raise_amount
            self.player_bet_amounts[action.player_seat] = (
                self.player_bet_amounts.get(action.player_seat, 0) + total_added
            )
            self.table.add_to_pot(total_added)
            self.highest_bet += action.amount
            self.min_raise_amount = action.amount
        elif action.action_type == ActionType.ALL_IN:
            chips_added = player.remove_chips(player.stack)
            self.player_bet_amounts[action.player_seat] = (
                self.player_bet_amounts.get(action.player_seat, 0) + chips_added
            )
            self.table.add_to_pot(chips_added)
            player.go_all_in()
            if chips_added > 0:
                self.highest_bet = max(self.highest_bet, chips_added)

        return True

    def get_next_to_act(self) -> Optional[int]:
        """Determine which player should act next.

        Returns:
            The seat number of the next player to act, or None if round is complete
        """
        if not self.table.get_active_players():
            self.round_complete = True
            return None

        if self.current_bettor_seat is None:
            # Start of round
            next_seat = self.start_seat
        else:
            # Get next player after current bettor
            next_seat = self.table.get_next_active_player(self.current_bettor_seat)
            if next_seat is None:
                # Check if round is complete
                if self._is_round_complete():
                    self.round_complete = True
                    return None
                else:
                    # Wrap around to start
                    next_seat = self.start_seat

        # Find next player who can act
        for i in range(self.table.num_seats):
            check_seat = (next_seat + i) % self.table.num_seats
            player = self.table.get_player(check_seat)
            if player and player.can_act():
                return check_seat

        self.round_complete = True
        return None

    def _is_round_complete(self) -> bool:
        """Check if the betting round is complete.

        Returns:
            True if all active players have either called the highest bet or folded
        """
        active_players = self.table.get_active_players()

        if len(active_players) <= 1:
            return True

        # All active players must have either:
        # 1. Called the highest bet, OR
        # 2. Be all-in with less than the highest bet
        for player in active_players:
            bet_amount = self.player_bet_amounts.get(player.seat, 0)
            # Check if player has called (bet amount equals highest) or is all-in
            if bet_amount < self.highest_bet and player.status != PlayerStatus.ALL_IN:
                return False

        return True

    def get_street_results(self) -> Dict:
        """Get a summary of the betting round results.

        Returns:
            Dictionary with round statistics
        """
        return {
            "num_actions": len(self.actions),
            "highest_bet": self.highest_bet,
            "total_bet": sum(self.player_bet_amounts.values()),
            "player_bet_amounts": self.player_bet_amounts.copy(),
            "actions": self.actions.copy(),
        }

    def get_players_all_in(self) -> List[int]:
        """Get seats of players who went all-in this round.

        Returns:
            List of seat numbers
        """
        all_in_seats = []
        for action in self.actions:
            if action.action_type == ActionType.ALL_IN:
                all_in_seats.append(action.player_seat)
        return all_in_seats
