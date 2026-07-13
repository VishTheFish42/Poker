"""Game controller orchestrating hand and round progression."""

from typing import Dict, List, Optional

from .action import Action, ActionType
from .betting import BettingRound
from .player import AIPlayer, HumanPlayer, Player, PlayerStatus
from .pot_manager import PotManager
from .showdown import Showdown, ShowdownResult
from .table import GameState, Table


class GameController:
    """Drives a hand of Texas Hold'em from deal to showdown.

    Owns a `Table` and coordinates `BettingRound`, `PotManager`, and
    `Showdown` across streets: posting blinds, dealing hole/community cards,
    advancing pre-flop -> flop -> turn -> river -> showdown, and rotating the
    dealer button between hands.

    Two ways to feed in a player's decision:
    - Directly via `submit_action()` / the convenience action verbs
      (`fold()`, `check_or_call()`, etc.) - the caller decides the action
      and pushes it in.
    - Indirectly via `auto_advance()`, which pulls the action from the
      current player itself through the polymorphic `Player.get_action()`
      interface: a `HumanPlayer` that already has a staged choice (set via
      `set_action()`), or an `AIPlayer` with an agent assigned. It loops
      through as many such turns as it can, stopping the moment a player
      needs real external input (or has no agent yet) or the hand ends.
      `start_new_hand()` calls this automatically, so a hand with an AI
      acting first doesn't stall waiting for an explicit call.
    """

    def __init__(self, table: Table, small_blind_amount: int, big_blind_amount: int) -> None:
        """Initialize the controller.

        Args:
            table: The Table to manage. Players should already be seated.
            small_blind_amount: The small blind stake.
            big_blind_amount: The big blind stake.
        """
        self.table = table
        self.small_blind_amount = small_blind_amount
        self.big_blind_amount = big_blind_amount
        self.pot_manager = PotManager()
        self.betting_round: Optional[BettingRound] = None
        self.total_contributions: Dict[int, int] = {}
        self.last_result: Optional[ShowdownResult] = None
        self.hand_number = 0
        self.log: List[str] = []

    def __repr__(self) -> str:
        """Return a string representation of the controller's current state."""
        return f"GameController({self.table.game_state}, pot=${self.table.total_pot})"

    @property
    def is_hand_complete(self) -> bool:
        """True once the current hand has finished (showdown or fold-win resolved)."""
        return self.table.game_state == GameState.HAND_COMPLETE

    def get_current_player(self) -> Optional[Player]:
        """Get the player who is currently on the clock.

        Returns:
            The Player whose turn it is, or None if no action is pending
            (e.g. between hands, or the hand is already complete).
        """
        if self.table.current_player_seat is None:
            return None
        return self.table.get_player(self.table.current_player_seat)

    def start_new_hand(self) -> None:
        """Begin a new hand: rotate the button, post blinds, deal hole cards,
        and open the pre-flop betting round.

        Raises:
            RuntimeError: If fewer than 2 seated players have chips left
                to play with (the game is effectively over) - checked
                before the button rotates, blinds post, or cards are
                dealt, so a caught error leaves `hand_number` and
                `last_result` (the previous hand's outcome) untouched.
        """
        self.table.reset_for_new_hand()

        if len(self.table.get_active_players()) < 2:
            raise RuntimeError(
                "Cannot start a new hand: fewer than 2 players have chips remaining."
            )

        self.pot_manager.reset()
        self.total_contributions = {}
        self.last_result = None
        self.hand_number += 1

        # Carry the controller's configured stakes into the table's own
        # blind bookkeeping so rotate_button() preserves them across hands.
        self.table.small_blind_amount = self.small_blind_amount
        self.table.big_blind_amount = self.big_blind_amount
        self.table.rotate_button()

        self.table.deck.shuffle()
        self.table.deal_hole_cards()

        button_player = self.table.get_player(self.table.button_seat)
        button_name = button_player.name if button_player else "?"
        self._log(f"=== Hand #{self.hand_number}: {button_name} is on the button ===")

        # Capture pre-blind stacks so the amounts actually posted can be
        # logged afterward even if the hand cascades straight past pre-flop
        # (e.g. a degenerate case where betting can't continue at all).
        sb_seat = self.table.small_blind_seat
        bb_seat = self.table.big_blind_seat
        sb_player = self.table.get_player(sb_seat) if sb_seat is not None else None
        bb_player = self.table.get_player(bb_seat) if bb_seat is not None else None
        sb_stack_before = sb_player.stack if sb_player else 0
        bb_stack_before = bb_player.stack if bb_player else 0

        self._start_betting_round()

        self._log_blind_posted(sb_player, sb_stack_before, "small blind")
        self._log_blind_posted(bb_player, bb_stack_before, "big blind")

        self.auto_advance()

    def _log_blind_posted(self, player: Optional[Player], stack_before: int, label: str) -> None:
        """Log a blind posting by comparing stack before/after, so it works
        even if the blind was short (all-in) or the hand already moved on.
        """
        if player is None:
            return
        posted = stack_before - player.stack
        if posted <= 0:
            return
        suffix = " (all-in)" if player.status == PlayerStatus.ALL_IN else ""
        self._log(f"{player.name} posts {label} ${posted}{suffix}.")

    def auto_advance(self) -> None:
        """Drive the hand forward through every player whose action can be
        determined without new external input right now.

        For each seat on the clock: if it's a `HumanPlayer` with an action
        already staged via `set_action()`, or an `AIPlayer` with an agent
        assigned, retrieve and submit that action, then repeat for whoever
        is up next. Stops as soon as the current player needs real input
        (a human with nothing staged, or an AI with no agent yet) or the
        hand is complete - the caller then supplies an action directly via
        `submit_action()` / a convenience method.
        """
        while not self.is_hand_complete:
            player = self.get_current_player()
            if player is None:
                return

            if isinstance(player, HumanPlayer):
                if player.pending_action is None:
                    return
            elif isinstance(player, AIPlayer):
                if player.ai_agent is None:
                    return
            else:
                return

            action = player.get_action(self._build_game_state_view())
            self.submit_action(action)

    def _build_game_state_view(self) -> Dict[str, object]:
        """Build a snapshot of the current state for a player's get_action().

        This is a generic, engine-level view - enough for a human UI
        callback or a simple AI policy to decide with. It is not the
        specialized observation encoding Phase 5's RL agents will use.
        """
        player = self.get_current_player()
        return {
            "street": self.table.game_state.value,
            "community_cards": list(self.table.community_cards),
            "pot": self.table.total_pot,
            "hole_cards": list(player.hole_cards) if player else [],
            "stack": player.stack if player else 0,
            "legal_actions": self.get_legal_actions(),
        }

    def submit_action(self, action: Action) -> None:
        """Apply an action for the player currently on the clock and
        automatically progress the hand (advance streets / resolve
        showdown) once the betting round is complete.

        Args:
            action: The action to apply.

        Raises:
            RuntimeError: If no betting round is in progress.
            ValueError: If it isn't the acting player's turn, or the action
                itself is invalid (validated by BettingRound).
        """
        if self.betting_round is None:
            raise RuntimeError("No betting round is in progress.")

        reason = self.validate_action(action)
        if reason is not None:
            raise ValueError(reason)

        acting_player = self.table.get_player(action.player_seat)
        if isinstance(acting_player, HumanPlayer):
            acting_player.action_required = False

        stack_before = acting_player.stack
        self.betting_round.process_action(action)
        self._log(self._describe_action(acting_player, action, stack_before))

        if len(self.table.get_players_in_hand()) <= 1:
            self._advance_after_round()
            return

        next_seat = self.betting_round.get_next_to_act()
        if next_seat is None:
            self._advance_after_round()
        else:
            self.table.set_current_player(next_seat)
            self._flag_if_waiting_on_human()

    # -- Convenience action verbs -------------------------------------
    # Thin wrappers around submit_action() that build the right Action for
    # the player currently on the clock, so a caller (UI button handler or
    # AI agent) never has to know seat numbers or engine-internal amount
    # conventions (e.g. that "call" becomes an all-in for a short stack).
    # Each one calls auto_advance() afterward, so any immediately-decidable
    # turns (staged human actions, AI players with an agent) play out
    # automatically rather than leaving the caller to notice and drive them.

    def fold(self) -> None:
        """Fold the current player's hand."""
        player = self._require_current_player()
        self.submit_action(Action(ActionType.FOLD, player.seat))
        self.auto_advance()

    def check_or_call(self) -> None:
        """Check if nothing is owed, otherwise call - going all-in instead
        if the player's stack can't cover the full call amount.
        """
        player = self._require_current_player()
        amount_to_call = self.betting_round.get_amount_to_call(player.seat)
        if amount_to_call == 0:
            self.submit_action(Action(ActionType.CHECK, player.seat))
        elif amount_to_call >= player.stack:
            self.submit_action(Action(ActionType.ALL_IN, player.seat, player.stack))
        else:
            self.submit_action(Action(ActionType.CALL, player.seat, amount_to_call))
        self.auto_advance()

    def bet(self, amount: int) -> None:
        """Open the betting for `amount` (only legal when no bet is owed yet)."""
        player = self._require_current_player()
        self.submit_action(Action(ActionType.BET, player.seat, amount))
        self.auto_advance()

    def raise_by(self, amount: int) -> None:
        """Raise by `amount` on top of the call already owed."""
        player = self._require_current_player()
        self.submit_action(Action(ActionType.RAISE, player.seat, amount))
        self.auto_advance()

    def go_all_in(self) -> None:
        """Push the current player's entire remaining stack into the pot."""
        player = self._require_current_player()
        self.submit_action(Action(ActionType.ALL_IN, player.seat, player.stack))
        self.auto_advance()

    def get_legal_actions(self) -> Dict[str, object]:
        """Describe what the player currently on the clock is allowed to do.

        Returns:
            A dict of booleans (`can_fold`, `can_check`, `can_call`,
            `can_bet`, `can_raise`, `can_all_in`) plus the relevant amounts
            (`call_amount`, `min_bet`, `min_raise`, `max_raise`) needed to
            build a legal bet/raise. `min_raise`/`max_raise` are "raise by"
            amounts, matching what `raise_by()` expects.
        """
        player = self._require_current_player()
        br = self.betting_round
        call_amount = br.get_amount_to_call(player.seat)
        stack = player.stack

        # Whether "opening" the betting is a BET or a RAISE hinges on whether
        # anyone has wagered anything this street yet (br.highest_bet), not on
        # whether *this* player currently owes a call: the big blind's
        # preflop option has call_amount == 0 (their blind already matches
        # the bet) but is still a raise in poker terms, since the blind
        # itself is a live wager.
        can_check = call_amount == 0
        # A call for exactly the player's whole stack is legal (BettingRound
        # allows call_amount <= stack); check_or_call() separately chooses to
        # route that specific case through ALL_IN for clarity, but it's not
        # a hard illegality here.
        can_call = 0 < call_amount <= stack
        can_bet = br.highest_bet == 0 and stack >= br.min_raise_amount
        can_raise = (
            br.highest_bet > 0
            and player.seat not in br.capped_seats
            and (stack - call_amount) >= br.min_raise_amount
        )

        return {
            "can_fold": True,
            "can_check": can_check,
            "can_call": can_call,
            "call_amount": call_amount,
            "can_bet": can_bet,
            "min_bet": br.min_raise_amount if can_bet else 0,
            "max_bet": stack,
            "can_raise": can_raise,
            "min_raise": br.min_raise_amount if can_raise else 0,
            "max_raise": max(0, stack - call_amount),
            "can_all_in": stack > 0,
        }

    def validate_action(self, action: Action) -> Optional[str]:
        """Check whether `action` would currently be legal, without applying it.

        This is a pure dry-run: it never mutates game state, so a UI can call
        it to validate a specific amount (e.g. from a bet slider) before the
        player confirms, or to explain why a button should be disabled.

        Args:
            action: The action to check.

        Returns:
            None if the action is legal right now, otherwise a short
            human-readable reason it isn't.
        """
        if self.betting_round is None:
            return "No betting round is in progress."
        if action.player_seat != self.table.current_player_seat:
            return (
                f"It is seat {self.table.current_player_seat}'s turn, "
                f"not seat {action.player_seat}'s."
            )

        legal = self.get_legal_actions()

        if action.action_type == ActionType.FOLD:
            return None
        if action.action_type == ActionType.CHECK:
            if not legal["can_check"]:
                return f"Cannot check: ${legal['call_amount']} is owed."
            return None
        if action.action_type == ActionType.CALL:
            if not legal["can_call"]:
                return "Cannot call right now (check, go all-in, or fold instead)."
            return None
        if action.action_type == ActionType.BET:
            if not legal["can_bet"]:
                return "Cannot bet right now (there may already be a bet to call - use raise instead)."
            if not (legal["min_bet"] <= action.amount <= legal["max_bet"]):
                return f"Bet must be between ${legal['min_bet']} and ${legal['max_bet']}."
            return None
        if action.action_type == ActionType.RAISE:
            if not legal["can_raise"]:
                return "Cannot raise right now."
            if not (legal["min_raise"] <= action.amount <= legal["max_raise"]):
                return f"Raise must be between ${legal['min_raise']} and ${legal['max_raise']}."
            return None
        if action.action_type == ActionType.ALL_IN:
            if not legal["can_all_in"]:
                return "No chips left to go all-in with."
            return None

        return f"Unknown action type: {action.action_type}"

    def is_waiting_for_human(self) -> bool:
        """True if the current player is a HumanPlayer waiting for UI input."""
        player = self.get_current_player()
        return isinstance(player, HumanPlayer) and player.action_required

    def get_action_prompt(self) -> Optional[str]:
        """Build a human-readable description of the decision facing
        whoever is currently on the clock: hole cards, board, pot, and the
        specific fold/check/call/bet/raise/all-in options available with
        their amounts.

        Returns:
            None if no one is currently on the clock, otherwise the prompt.
        """
        player = self.get_current_player()
        if player is None:
            return None

        legal = self.get_legal_actions()
        hole = " ".join(repr(c) for c in player.hole_cards)
        board = " ".join(repr(c) for c in self.table.community_cards)

        options = ["fold"]
        if legal["can_check"]:
            options.append("check")
        if legal["can_call"]:
            options.append(f"call ${legal['call_amount']}")
        if legal["can_bet"]:
            options.append(f"bet ${legal['min_bet']}-${legal['max_bet']}")
        if legal["can_raise"]:
            options.append(f"raise ${legal['min_raise']}-${legal['max_raise']}")
        if legal["can_all_in"]:
            options.append("all-in")

        lines = [f"{player.name}'s turn ({self.table.game_state.value})."]
        if board:
            lines.append(f"Board: {board}.")
        if hole:
            lines.append(f"Your hand: {hole}.")
        lines.append(f"Pot: ${self.table.total_pot}.")
        lines.append("Options: " + ", ".join(options) + ".")
        return " ".join(lines)

    def _describe_action(self, player: Player, action: Action, stack_before: int) -> str:
        """Build a human-readable game-log line for an action just taken."""
        chips_paid = stack_before - player.stack
        total_bet = (
            self.betting_round.player_bet_amounts.get(player.seat, chips_paid)
            if self.betting_round
            else chips_paid
        )
        all_in_suffix = " and is all-in" if player.status == PlayerStatus.ALL_IN else ""

        if action.action_type == ActionType.FOLD:
            return f"{player.name} folds."
        if action.action_type == ActionType.CHECK:
            return f"{player.name} checks."
        if action.action_type == ActionType.CALL:
            return f"{player.name} calls ${chips_paid}{all_in_suffix}."
        if action.action_type == ActionType.BET:
            return f"{player.name} bets ${chips_paid}{all_in_suffix}."
        if action.action_type == ActionType.RAISE:
            return f"{player.name} raises to ${total_bet}{all_in_suffix}."
        if action.action_type == ActionType.ALL_IN:
            return f"{player.name} goes all-in for ${total_bet}."
        return f"{player.name}: {action}"

    def _log(self, message: str) -> None:
        """Append a line to the game log."""
        self.log.append(message)

    def _require_current_player(self) -> Player:
        """Get the current player, raising if no action is pending."""
        if self.betting_round is None:
            raise RuntimeError("No betting round is in progress.")
        player = self.get_current_player()
        if player is None:
            raise RuntimeError("No player is currently on the clock.")
        return player

    def _flag_if_waiting_on_human(self) -> None:
        """Mark a HumanPlayer as needing UI input when it becomes their turn."""
        player = self.get_current_player()
        if isinstance(player, HumanPlayer):
            player.action_required = True

    def _start_betting_round(self) -> None:
        """Create and open the BettingRound for the current street."""
        start_seat = self._first_to_act_seat()
        self.betting_round = BettingRound(
            self.table, self.small_blind_amount, self.big_blind_amount, start_seat
        )
        if self.table.game_state == GameState.PRE_FLOP:
            self.betting_round.initialize_blinds()

        if not self._betting_can_continue():
            # Fewer than 2 players can still act (e.g. one live player left
            # against all-in opponents who can't respond) - there's no one
            # left to bet against, so run the hand forward without opening
            # betting on this or any later street.
            self._advance_after_round()
            return

        next_seat = self.betting_round.get_next_to_act()
        if next_seat is None:
            self._advance_after_round()
        else:
            self.table.set_current_player(next_seat)
            self._flag_if_waiting_on_human()

    def _betting_can_continue(self) -> bool:
        """True if 2+ players can still make a betting decision this street.

        A single remaining live player facing only all-in (or folded)
        opponents has no one who could call/raise in response, so betting
        should stop and the rest of the board should be dealt automatically.
        """
        return sum(1 for p in self.table.get_active_players() if p.can_act()) >= 2

    def _first_to_act_seat(self) -> int:
        """Determine the seat that acts first on the current street."""
        if self.table.game_state == GameState.PRE_FLOP:
            anchor = self.table.big_blind_seat
        else:
            anchor = self.table.button_seat

        seat = self.table.get_next_active_player(anchor)
        return seat if seat is not None else anchor

    def _accumulate_contributions(self) -> None:
        """Fold this street's bets into the hand-long contribution totals
        that PotManager needs for side-pot calculation.
        """
        if self.betting_round is None:
            return
        for seat, amount in self.betting_round.player_bet_amounts.items():
            self.total_contributions[seat] = self.total_contributions.get(seat, 0) + amount

    def _advance_after_round(self) -> None:
        """Called once the current street's betting is settled: fold its
        contributions in, then move to the next street, showdown, or the
        end of the hand.
        """
        self._accumulate_contributions()

        if len(self.table.get_players_in_hand()) <= 1:
            self._go_to_showdown()
            return

        if self.table.game_state == GameState.RIVER:
            self._go_to_showdown()
            return

        self.table.advance_street()
        self._log_street()
        self._start_betting_round()

    def _log_street(self) -> None:
        """Log the community cards revealed for the current street."""
        label = {"flop": "Flop", "turn": "Turn", "river": "River"}.get(
            self.table.game_state.value, self.table.game_state.value
        )
        board = " ".join(repr(c) for c in self.table.community_cards)
        self._log(f"-- {label}: {board} (pot: ${self.table.total_pot}) --")

    def _go_to_showdown(self) -> None:
        """Resolve the hand: deal out any remaining board (for an all-in
        runout) if needed, award pots, and credit winners' stacks.
        """
        players_in_hand = self.table.get_players_in_hand()

        if len(players_in_hand) > 1:
            # All-in runout: deal whatever community cards are still missing.
            while len(self.table.community_cards) < 5:
                self.table.advance_street()
                self._log_street()
            self.table.game_state = GameState.SHOWDOWN

        self.pot_manager.calculate_pots(self.total_contributions)
        self.last_result = Showdown.resolve(
            players_in_hand, self.table.community_cards, self.pot_manager
        )
        self._log_showdown_result()

        self.betting_round = None
        self.table.current_player_seat = None
        self.table.game_state = GameState.HAND_COMPLETE

    def _log_showdown_result(self) -> None:
        """Log the hand's outcome: revealed hands and winnings, or an
        uncontested pot if everyone else folded.
        """
        result = self.last_result
        if result is None:
            return

        if result.is_showdown:
            for r in result.player_results:
                hole = " ".join(repr(c) for c in r.hole_cards)
                hand_desc = r.best_hand.hand_type.name.replace("_", " ").title() if r.best_hand else "?"
                self._log(f"{r.name} shows {hole} ({hand_desc}).")
            for winner in result.winners:
                self._log(f"{winner.name} wins ${winner.chips_won}.")
        else:
            for r in result.player_results:
                if r.chips_won > 0:
                    self._log(f"{r.name} wins the pot uncontested (${r.chips_won}).")
