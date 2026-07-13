"""Unit tests for betting round management."""

import pytest
from src.poker.engine.betting import BettingRound
from src.poker.engine.table import Table
from src.poker.engine.action import Action, ActionType
from src.poker.engine.player import Player, PlayerStatus


class TestBettingRound:
    """Test cases for BettingRound class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.table = Table(6)
        self.players = [Player("Player" + str(i), i, 1000) for i in range(3)]
        for player in self.players:
            self.table.add_player(player)
        self.table.set_blinds(0, 1, 2)

    def test_betting_round_initialization(self):
        """Test betting round initialization."""
        br = BettingRound(self.table, 1, 2, 1)
        assert br.table == self.table
        assert br.small_blind_amount == 1
        assert br.big_blind_amount == 2
        assert br.start_seat == 1
        assert len(br.actions) == 0
        assert br.table.total_pot == 0

    def test_initialize_blinds(self):
        """Test blind posting."""
        br = BettingRound(self.table, 1, 2, 1)
        br.initialize_blinds()

        sb_player = self.table.get_player(1)
        bb_player = self.table.get_player(2)

        # Small blind should have bet 1
        assert br.player_bet_amounts[1] == 1
        assert sb_player.stack == 999

        # Big blind should have bet 2
        assert br.player_bet_amounts[2] == 2
        assert bb_player.stack == 998

        # Pot should be 3
        assert self.table.total_pot == 3

    def test_get_amount_to_call(self):
        """Test calculating amount to call."""
        br = BettingRound(self.table, 1, 2, 1)
        br.initialize_blinds()

        # For button (seat 0), nothing bet yet, highest is 2
        assert br.get_amount_to_call(0) == 2

        # For small blind (seat 1), already bet 1, needs 1 more
        assert br.get_amount_to_call(1) == 1

        # For big blind (seat 2), already bet 2, nothing to call
        assert br.get_amount_to_call(2) == 0

    def test_can_check(self):
        """Test checking if player can check."""
        br = BettingRound(self.table, 1, 2, 1)
        br.initialize_blinds()

        assert not br.can_check(0)  # Must call 2
        assert not br.can_check(1)  # Must call 1
        assert br.can_check(2)  # No amount to call

    def test_fold_action(self):
        """Test processing a fold action."""
        br = BettingRound(self.table, 1, 2, 1)
        br.initialize_blinds()

        player = self.table.get_player(0)
        action = Action(ActionType.FOLD, 0)
        br.process_action(action)

        assert len(br.actions) == 1
        assert player.status == PlayerStatus.FOLDED

    def test_check_action(self):
        """Test processing a check action."""
        br = BettingRound(self.table, 1, 2, 1)
        br.initialize_blinds()

        player = self.table.get_player(2)  # Big blind, can check
        action = Action(ActionType.CHECK, 2)
        br.process_action(action)

        assert len(br.actions) == 1
        assert player.stack == 998  # No change from blind posting

    def test_check_invalid(self):
        """Test that checking with amount to call is invalid."""
        br = BettingRound(self.table, 1, 2, 1)
        br.initialize_blinds()

        player = self.table.get_player(0)  # Has 2 to call
        action = Action(ActionType.CHECK, 0)

        with pytest.raises(ValueError):
            br.process_action(action)

    def test_call_action(self):
        """Test processing a call action."""
        br = BettingRound(self.table, 1, 2, 1)
        br.initialize_blinds()

        player = self.table.get_player(0)  # Has 2 to call
        initial_stack = player.stack
        action = Action(ActionType.CALL, 0, 2)
        br.process_action(action)

        assert len(br.actions) == 1
        assert player.stack == initial_stack - 2
        assert br.player_bet_amounts[0] == 2
        assert self.table.total_pot == 5  # 1 + 2 + 2

    def test_bet_action(self):
        """Test processing a bet action on a fresh street (nothing to call)."""
        br = BettingRound(self.table, 1, 2, 1)
        # Flop-style round: no blinds posted, no bet yet.
        player = self.table.get_player(0)
        initial_stack = player.stack
        action = Action(ActionType.BET, 0, 50)
        br.process_action(action)

        assert len(br.actions) == 1
        assert player.stack == initial_stack - 50
        assert br.player_bet_amounts[0] == 50
        assert br.highest_bet == 50
        assert br.min_raise_amount == 50
        assert self.table.total_pot == 50

    def test_bet_below_minimum_rejected(self):
        """A bet smaller than min_raise_amount (the big blind, on a fresh
        street) is not a legal opening bet - the player must bet at least
        the minimum, or go all-in for their whole (short) stack instead.
        """
        br = BettingRound(self.table, 1, 2, 1)  # big_blind_amount=2
        action = Action(ActionType.BET, 0, 1)

        with pytest.raises(ValueError):
            br.process_action(action)

    def test_bet_after_prior_contribution_this_round(self):
        """A BET from a player who already has chips in this round (e.g. the
        big blind exercising its option to raise) must count their FULL
        round total in highest_bet, not just the newly added chips.
        """
        br = BettingRound(self.table, 1, 2, 1)
        br.initialize_blinds()
        br.process_action(Action(ActionType.CALL, 0, 2))  # button calls
        br.process_action(Action(ActionType.CALL, 1, 1))  # SB calls

        # BB (already has $2 in from the blind) bets $50 more instead of checking.
        br.process_action(Action(ActionType.BET, 2, 50))

        assert br.player_bet_amounts[2] == 52
        assert br.highest_bet == 52
        assert br.get_amount_to_call(0) == 50  # seat 0 already has $2 in from its earlier call

    def test_all_in_action(self):
        """Test processing an all-in action."""
        br = BettingRound(self.table, 1, 2, 1)
        br.initialize_blinds()

        player = self.table.get_player(0)
        initial_stack = player.stack
        action = Action(ActionType.ALL_IN, 0, initial_stack)
        br.process_action(action)

        assert len(br.actions) == 1
        assert player.stack == 0
        assert player.status == PlayerStatus.ALL_IN
        assert br.player_bet_amounts[0] == initial_stack

    def test_raise_action(self):
        """Test processing a raise action."""
        br = BettingRound(self.table, 1, 2, 1)
        br.initialize_blinds()

        player = self.table.get_player(0)

        # First action: call the 2 big blind
        action1 = Action(ActionType.CALL, 0, 2)
        br.process_action(action1)

        # Small blind now has 2 to call (was 1, big blind called 2)
        action2 = Action(ActionType.CALL, 1, 1)
        br.process_action(action2)

        # Big blind raises to 6 (bet 4 more)
        bb_player = self.table.get_player(2)
        action3 = Action(ActionType.RAISE, 2, 4)

        # Process raise
        br.highest_bet = 2
        br.player_bet_amounts[0] = 2
        br.player_bet_amounts[1] = 1
        br.player_bet_amounts[2] = 2
        br.highest_bet = 2
        br.process_action(action3)

        assert len(br.actions) == 3
        assert bb_player.stack < 998
        assert br.highest_bet == 6

    def test_call_with_entire_stack_marks_all_in(self):
        """A plain CALL that exhausts a player's stack must mark them ALL_IN,
        not leave them ACTIVE with $0 (which would make can_act() wrongly
        keep asking them to act on later streets with nothing left to bet).
        """
        table = Table(3)
        players = [Player("P" + str(i), i, 1000) for i in range(3)]
        for player in players:
            table.add_player(player)
        table.set_blinds(0, 1, 2)

        short_stack = table.get_player(1)
        short_stack.stack = 5  # will be fully used up calling a $5 bet

        br = BettingRound(table, 1, 2, 1)
        br.highest_bet = 5
        action = Action(ActionType.CALL, 1, 5)
        br.process_action(action)

        assert short_stack.stack == 0
        assert short_stack.status == PlayerStatus.ALL_IN

    def test_short_blind_marks_all_in(self):
        """Posting a blind with less than the full blind amount (because the
        stack is smaller) must mark the player ALL_IN, not leave them ACTIVE
        with $0 unable to take any valid action on the next street.
        """
        table = Table(3)
        players = [Player("P" + str(i), i, 1000) for i in range(3)]
        for player in players:
            table.add_player(player)
        table.set_blinds(0, 1, 2)

        short_bb = table.get_player(2)
        short_bb.stack = 1  # less than the $2 big blind

        br = BettingRound(table, 1, 2, 1)
        br.initialize_blinds()

        assert short_bb.stack == 0
        assert short_bb.status == PlayerStatus.ALL_IN

    def test_get_next_to_act(self):
        """Test determining next player to act."""
        br = BettingRound(self.table, 1, 2, 1)
        br.initialize_blinds()

        next_seat = br.get_next_to_act()
        assert next_seat == 1  # Should be small blind

        # Small blind needs to call, not check
        action = Action(ActionType.CALL, 1, 1)
        br.process_action(action)
        # At this point we've processed one action
        assert len(br.actions) == 1

    def test_get_next_to_act_advances_and_terminates(self):
        """get_next_to_act must move to the NEXT player after each action and
        must eventually return None once everyone has matched the bet -
        it must not get stuck repeating the same seat forever.
        """
        br = BettingRound(self.table, 1, 2, 1)
        br.initialize_blinds()

        order = []
        for _ in range(10):  # safety cap; a correct round finishes in 3 steps
            nxt = br.get_next_to_act()
            order.append(nxt)
            if nxt is None:
                break
            amt = br.get_amount_to_call(nxt)
            action = Action(ActionType.CALL, nxt, amt) if amt > 0 else Action(ActionType.CHECK, nxt)
            br.process_action(action)

        # Starting at seat 1 (small blind): SB calls, BB checks its option,
        # button calls last, then the round is complete.
        assert order == [1, 2, 0, None]
        assert br.round_complete

    def test_check_around_requires_every_player_to_act(self):
        """With no bet yet (highest_bet=0), the round must not be declared
        complete just because bet amounts trivially match - each player must
        actually act (check) at least once.
        """
        br = BettingRound(self.table, 1, 2, 1)  # no initialize_blinds(): fresh street

        first = br.get_next_to_act()
        br.process_action(Action(ActionType.CHECK, first))
        assert not br._is_round_complete()  # other two players haven't acted yet

        second = br.get_next_to_act()
        assert second is not None and second != first
        br.process_action(Action(ActionType.CHECK, second))
        assert not br._is_round_complete()

        third = br.get_next_to_act()
        assert third is not None and third not in (first, second)
        br.process_action(Action(ActionType.CHECK, third))
        assert br._is_round_complete()

    def test_raise_reopens_action_for_players_who_already_acted(self):
        """A raise must force players who already matched the old bet to act again."""
        br = BettingRound(self.table, 1, 2, 1)
        br.initialize_blinds()

        # Button calls the big blind.
        br.process_action(Action(ActionType.CALL, 0, 2))
        # Small blind calls too - everyone has now matched $2, except BB's option.
        br.process_action(Action(ActionType.CALL, 1, 1))
        # Big blind raises instead of checking its option.
        br.process_action(Action(ActionType.RAISE, 2, 4))

        # Button and small blind already "acted" under the old bet level but
        # must be forced to respond again to the raise.
        assert not br._is_round_complete()
        assert br.get_next_to_act() == 0

    def test_is_round_complete(self):
        """Test checking if round is complete."""
        br = BettingRound(self.table, 1, 2, 1)
        br.initialize_blinds()

        # All players need to act
        assert not br._is_round_complete()

        # Process actions until complete
        # Button calls
        action1 = Action(ActionType.CALL, 0, 2)
        br.process_action(action1)

        # Small blind calls (needs 1 more to match big blind)
        action2 = Action(ActionType.CALL, 1, 1)
        br.process_action(action2)

        # Big blind checks (already has highest bet)
        action3 = Action(ActionType.CHECK, 2)
        br.process_action(action3)

        # Now everyone has equal bets
        assert br._is_round_complete()

    def test_get_players_all_in(self):
        """Test getting list of players who went all-in."""
        br = BettingRound(self.table, 1, 2, 1)
        br.initialize_blinds()

        assert len(br.get_players_all_in()) == 0

        player = self.table.get_player(0)
        action = Action(ActionType.ALL_IN, 0, player.stack)
        br.process_action(action)

        all_in_seats = br.get_players_all_in()
        assert 0 in all_in_seats

    def test_all_in_after_prior_bet_this_round(self):
        """All-in from a player who already has chips in for the round (e.g.
        the big blind) must count their FULL round total toward highest_bet,
        not just the incremental chips added by the all-in action.
        """
        br = BettingRound(self.table, 1, 2, 1)
        br.initialize_blinds()

        bb_player = self.table.get_player(2)  # already has $2 in from the blind
        bb_stack_before = bb_player.stack
        action = Action(ActionType.ALL_IN, 2, bb_stack_before)
        br.process_action(action)

        expected_total = 2 + bb_stack_before  # blind already posted + all-in chips
        assert br.player_bet_amounts[2] == expected_total
        assert br.highest_bet == expected_total
        # Another player should now owe the full total, not just the shove amount
        assert br.get_amount_to_call(0) == expected_total

    def test_incomplete_all_in_raise_caps_previously_acted_players(self):
        """An all-in that raises the bet by LESS than a full raise increment
        ("incomplete raise") must not reopen re-raising rights for players
        who already matched the old bet - they may only call the extra
        amount or fold, not raise again. A subsequent FULL raise clears
        the cap for everyone.
        """
        table = Table(4)
        players = [Player("P" + str(i), i, 1000) for i in range(4)]
        for player in players:
            table.add_player(player)
        table.set_blinds(0, 50, 100)

        br = BettingRound(table, 50, 100, start_seat=3)  # UTG in 4-handed
        br.initialize_blinds()
        br.process_action(Action(ActionType.CALL, 3, 100))  # UTG calls the $100 BB

        players[0].stack = 150  # button can only shove for 150 (a $50 raise - incomplete)
        br.process_action(Action(ActionType.ALL_IN, 0, 150))

        assert 3 in br.capped_seats  # UTG already matched the old bet, now capped
        with pytest.raises(ValueError):
            br.process_action(Action(ActionType.RAISE, 3, 200))

        # UTG can still call the extra amount.
        br.process_action(Action(ActionType.CALL, 3, br.get_amount_to_call(3)))
        assert br.player_bet_amounts[3] == 150

        # A subsequent FULL raise (from a player who hadn't acted yet) clears the cap.
        players[1].stack = 1000
        br.process_action(Action(ActionType.RAISE, 1, 200))
        assert br.capped_seats == set()

    def test_full_all_in_raise_does_not_cap_anyone(self):
        """An all-in that raises by AT LEAST a full raise increment behaves
        like a normal raise: it fully reopens the action, with no cap.
        """
        table = Table(4)
        players = [Player("P" + str(i), i, 1000) for i in range(4)]
        for player in players:
            table.add_player(player)
        table.set_blinds(0, 50, 100)

        br = BettingRound(table, 50, 100, start_seat=3)
        br.initialize_blinds()
        br.process_action(Action(ActionType.CALL, 3, 100))

        players[0].stack = 300  # a full $200 raise on top of the $100 bet
        br.process_action(Action(ActionType.ALL_IN, 0, 300))

        assert br.capped_seats == set()
        # UTG (already called $100, stack correspondingly reduced) should be
        # free to re-raise in response to this full raise.
        br.process_action(Action(ActionType.RAISE, 3, 300))
        assert br.highest_bet == 600

    def test_street_results(self):
        """Test getting street results."""
        br = BettingRound(self.table, 1, 2, 1)
        br.initialize_blinds()

        results = br.get_street_results()
        assert "num_actions" in results
        assert "highest_bet" in results
        assert "total_bet" in results
        assert "player_bet_amounts" in results
        assert "actions" in results


class TestBettingRoundIntegration:
    """Integration tests for betting rounds."""

    def test_pre_flop_betting_scenario(self):
        """Test a pre-flop betting scenario."""
        table = Table(6)
        players = [Player("Player" + str(i), i, 1000) for i in range(3)]
        for player in players:
            table.add_player(player)

        table.set_blinds(0, 1, 2)
        br = BettingRound(table, 1, 2, 1)
        br.initialize_blinds()

        # Button folds
        action1 = Action(ActionType.FOLD, 0)
        br.process_action(action1)

        # Small blind calls big blind
        action2 = Action(ActionType.CALL, 1, 1)
        br.process_action(action2)

        # Big blind checks
        action3 = Action(ActionType.CHECK, 2)
        br.process_action(action3)

        # Check results
        results = br.get_street_results()
        assert results["num_actions"] == 3
        assert table.get_player(0).status == PlayerStatus.FOLDED

    def test_multiple_raises_scenario(self):
        """Test scenario with multiple raises."""
        table = Table(6)
        players = [Player("Player" + str(i), i, 5000) for i in range(3)]
        for player in players:
            table.add_player(player)

        table.set_blinds(0, 25, 50)
        br = BettingRound(table, 25, 50, 1)
        br.initialize_blinds()

        # Button calls the 50 big blind
        action1 = Action(ActionType.CALL, 0, 50)
        br.process_action(action1)

        # Small blind calls (needs 25 more to match BB)
        action2 = Action(ActionType.CALL, 1, 25)
        br.process_action(action2)

        # Big blind raises to 175 (bet 125 more on top of 50)
        action3 = Action(ActionType.RAISE, 2, 125)
        br.process_action(action3)

        # When SB raises by 125 on top of existing 50, highest_bet becomes 175
        assert br.highest_bet == 175


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
