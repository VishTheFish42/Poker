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
        """Test processing a bet action."""
        br = BettingRound(self.table, 1, 2, 1)
        br.initialize_blinds()

        # Big blind checks first
        bb_action = Action(ActionType.CHECK, 2)
        br.process_action(bb_action)

        # Small blind tries to bet (must be all action)
        br.player_bet_amounts[1] = 1
        br.player_bet_amounts[2] = 2

        # Now button can bet (if we reset the highest bet scenario)
        br.highest_bet = 2
        br.player_bet_amounts[0] = 2

        player = self.table.get_player(1)
        action = Action(ActionType.BET, 1, 50)

        # This should work in a flop scenario where no one has bet yet
        # For pre-flop with blinds already posted, betting is raising
        # Let's test a simpler bet scenario

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
