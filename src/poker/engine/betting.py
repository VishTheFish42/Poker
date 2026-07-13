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
        # Seats that have acted since the last bet/raise reopened the action.
        # A round is only complete once every player still able to act is in
        # this set *and* has matched the highest bet.
        self.acted_seats: set = set()
        # Seats that may only call or fold right now, not raise again. This
        # is populated when an all-in raises the bet by less than a full
        # raise increment ("incomplete raise"): players who already acted at
        # the previous level must still respond to the extra amount, but an
        # incomplete raise does not reopen their right to re-raise - only a
        # full raise does. Cleared whenever a full bet/raise occurs.
        self.capped_seats: set = set()

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
                if sb_player.stack == 0:
                    sb_player.go_all_in()

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
                if bb_player.stack == 0:
                    bb_player.go_all_in()

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
            if action.amount < self.min_raise_amount:
                raise ValueError(
                    f"Bet of ${action.amount} is less than the minimum bet of "
                    f"${self.min_raise_amount} (go all-in to bet less)"
                )
        elif action.action_type == ActionType.RAISE:
            if action.player_seat in self.capped_seats:
                raise ValueError(
                    "Cannot raise: facing an incomplete all-in raise, "
                    "may only call or fold"
                )
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
        self.current_bettor_seat = action.player_seat

        if action.action_type == ActionType.FOLD:
            player.fold()
            self.acted_seats.add(action.player_seat)
        elif action.action_type == ActionType.CHECK:
            # No chips added
            self.acted_seats.add(action.player_seat)
        elif action.action_type == ActionType.CALL:
            chips_added = player.remove_chips(amount_to_call)
            self.player_bet_amounts[action.player_seat] = (
                self.player_bet_amounts.get(action.player_seat, 0) + chips_added
            )
            self.table.add_to_pot(chips_added)
            self.acted_seats.add(action.player_seat)
        elif action.action_type == ActionType.BET:
            chips_added = player.remove_chips(action.amount)
            self.player_bet_amounts[action.player_seat] = (
                self.player_bet_amounts.get(action.player_seat, 0) + chips_added
            )
            self.table.add_to_pot(chips_added)
            # BET is only legal when amount_to_call is 0, so this player's
            # existing bet_amount already equals the old highest_bet (e.g.
            # the big blind's option to raise over its own posted blind).
            self.highest_bet += chips_added
            self.min_raise_amount = chips_added
            # A new (full) bet reopens the action for everyone, with no cap.
            self.acted_seats = {action.player_seat}
            self.capped_seats = set()
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
            # A full raise reopens the action for everyone, with no cap.
            self.acted_seats = {action.player_seat}
            self.capped_seats = set()
        elif action.action_type == ActionType.ALL_IN:
            chips_added = player.remove_chips(player.stack)
            new_total = self.player_bet_amounts.get(action.player_seat, 0) + chips_added
            self.player_bet_amounts[action.player_seat] = new_total
            self.table.add_to_pot(chips_added)
            player.go_all_in()
            if new_total > self.highest_bet:
                raise_size = new_total - self.highest_bet
                is_full_raise = raise_size >= self.min_raise_amount
                if is_full_raise:
                    self.min_raise_amount = raise_size
                    # A full raise reopens the action for everyone, with no cap.
                    self.capped_seats = set()
                else:
                    # Incomplete raise: everyone who already matched the old
                    # bet must still respond to the extra amount, but may
                    # only call or fold - this all-in was too small to
                    # reopen their right to re-raise.
                    self.capped_seats |= self.acted_seats - {action.player_seat}
                self.highest_bet = new_total
                self.acted_seats = {action.player_seat}
            else:
                self.acted_seats.add(action.player_seat)

        # Any action that exhausts a player's stack makes them all-in,
        # regardless of which action type was used to get there.
        if action.action_type != ActionType.FOLD and player.stack == 0:
            player.go_all_in()

        return True

    def get_next_to_act(self) -> Optional[int]:
        """Determine which player should act next.

        Returns:
            The seat number of the next player to act, or None if round is complete
        """
        if not self.table.get_active_players():
            self.round_complete = True
            return None

        # Check completion first: with 2+ active players, cycling through
        # get_next_active_player alone never terminates on its own, since it
        # only skips folded/all-in/sitting-out seats, not seats that have
        # already matched the current bet.
        if self.current_bettor_seat is not None and self._is_round_complete():
            self.round_complete = True
            return None

        if self.current_bettor_seat is None:
            # Start of round
            next_seat = self.start_seat
        else:
            # Get next player after current bettor
            next_seat = self.table.get_next_active_player(self.current_bettor_seat)
            if next_seat is None:
                self.round_complete = True
                return None

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
            True if every active player has both acted since the last bet/raise
            and matched the highest bet (or is all-in).
        """
        active_players = self.table.get_active_players()

        if len(active_players) <= 1:
            return True

        for player in active_players:
            if player.status == PlayerStatus.ALL_IN:
                continue
            if player.seat not in self.acted_seats:
                return False
            bet_amount = self.player_bet_amounts.get(player.seat, 0)
            if bet_amount < self.highest_bet:
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
