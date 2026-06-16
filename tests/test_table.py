"""Unit tests for table and game state management."""

import pytest
from src.poker.engine.table import Table, GameState
from src.poker.engine.player import Player, HumanPlayer, AIPlayer, PlayerStatus, Difficulty
from src.poker.engine.card import CardRank, CardSuit


class TestGameState:
    """Test cases for GameState enum."""

    def test_game_states_exist(self):
        """Test that all game states exist."""
        assert GameState.PRE_FLOP
        assert GameState.FLOP
        assert GameState.TURN
        assert GameState.RIVER
        assert GameState.SHOWDOWN
        assert GameState.HAND_COMPLETE

    def test_game_state_string(self):
        """Test game state string representation."""
        assert str(GameState.PRE_FLOP) == "pre_flop"
        assert str(GameState.FLOP) == "flop"

    def test_street_numbers(self):
        """Test street number mapping."""
        assert GameState.PRE_FLOP.street_number == 0
        assert GameState.FLOP.street_number == 1
        assert GameState.TURN.street_number == 2
        assert GameState.RIVER.street_number == 3
        assert GameState.SHOWDOWN.street_number == 4


class TestTable:
    """Test cases for Table class."""

    def test_table_initialization(self):
        """Test table initialization."""
        table = Table(6)
        assert table.num_seats == 6
        assert len(table.seats) == 6
        assert table.game_state == GameState.PRE_FLOP
        assert table.total_pot == 0
        assert len(table.community_cards) == 0

    def test_table_invalid_seats(self):
        """Test that invalid seat counts raise error."""
        with pytest.raises(ValueError):
            Table(1)
        with pytest.raises(ValueError):
            Table(11)

    def test_add_player(self):
        """Test adding a player to the table."""
        table = Table(6)
        player = Player("Alice", 0, 1000)
        table.add_player(player)
        assert table.get_player(0) == player
        assert table.seats[0].is_occupied()

    def test_add_player_invalid_seat(self):
        """Test adding player to invalid seat raises error."""
        table = Table(6)
        player = Player("Alice", 10, 1000)
        with pytest.raises(ValueError):
            table.add_player(player)

    def test_add_player_occupied_seat(self):
        """Test adding player to occupied seat raises error."""
        table = Table(6)
        player1 = Player("Alice", 0, 1000)
        player2 = Player("Bob", 0, 1000)
        table.add_player(player1)
        with pytest.raises(ValueError):
            table.add_player(player2)

    def test_remove_player(self):
        """Test removing a player from the table."""
        table = Table(6)
        player = Player("Alice", 0, 1000)
        table.add_player(player)
        removed = table.remove_player(0)
        assert removed == player
        assert table.get_player(0) is None

    def test_get_all_players(self):
        """Test getting all players at the table."""
        table = Table(6)
        players = [
            Player("Alice", 0, 1000),
            Player("Bob", 2, 1000),
            Player("Charlie", 4, 1000),
        ]
        for player in players:
            table.add_player(player)

        all_players = table.get_all_players()
        assert len(all_players) == 3
        assert all(p in all_players for p in players)

    def test_get_active_players(self):
        """Test getting active players."""
        table = Table(6)
        player1 = Player("Alice", 0, 1000)
        player2 = Player("Bob", 1, 1000)
        table.add_player(player1)
        table.add_player(player2)

        assert len(table.get_active_players()) == 2
        player1.fold()
        assert len(table.get_active_players()) == 1

    def test_set_blinds(self):
        """Test setting blind positions."""
        table = Table(6)
        players = [
            Player("Alice", i, 1000) for i in range(6)
        ]
        for player in players:
            table.add_player(player)

        table.set_blinds(0, 1, 2)
        assert table.button_seat == 0
        assert table.small_blind_seat == 1
        assert table.big_blind_seat == 2
        assert table.seats[0].is_button
        assert table.seats[1].is_small_blind
        assert table.seats[2].is_big_blind

    def test_advance_street(self):
        """Test advancing through streets."""
        table = Table(6)
        assert table.game_state == GameState.PRE_FLOP

        state = table.advance_street()
        assert state == GameState.FLOP
        assert len(table.community_cards) == 3

        state = table.advance_street()
        assert state == GameState.TURN
        assert len(table.community_cards) == 4

        state = table.advance_street()
        assert state == GameState.RIVER
        assert len(table.community_cards) == 5

        state = table.advance_street()
        assert state == GameState.SHOWDOWN

    def test_get_next_active_player(self):
        """Test getting next active player."""
        table = Table(6)
        players = [Player("Player" + str(i), i, 1000) for i in range(6)]
        for player in players:
            table.add_player(player)

        players[1].fold()
        next_seat = table.get_next_active_player(0)
        assert next_seat == 2  # Skips folded player 1

    def test_get_previous_active_player(self):
        """Test getting previous active player."""
        table = Table(6)
        players = [Player("Player" + str(i), i, 1000) for i in range(6)]
        for player in players:
            table.add_player(player)

        players[4].fold()
        prev_seat = table.get_previous_active_player(5)
        assert prev_seat == 3  # Skips folded player 4

    def test_reset_for_new_hand(self):
        """Test resetting table for new hand."""
        table = Table(6)
        player = Player("Alice", 0, 1000)
        table.add_player(player)
        player.fold()
        player.current_bet = 50
        table.total_pot = 100
        table.community_cards = [None, None, None]  # Mock cards

        table.reset_for_new_hand()
        assert player.status == PlayerStatus.ACTIVE
        assert player.current_bet == 0
        assert table.total_pot == 0
        assert len(table.community_cards) == 0
        assert table.game_state == GameState.PRE_FLOP

    def test_pot_management(self):
        """Test pot management."""
        table = Table(6)
        assert table.total_pot == 0

        table.add_to_pot(50)
        assert table.total_pot == 50

        table.add_to_pot(100)
        assert table.total_pot == 150

        table.set_pot(200)
        assert table.total_pot == 200

    def test_deal_hole_cards(self):
        """Test dealing hole cards."""
        table = Table(6)
        players = [Player("Player" + str(i), i, 1000) for i in range(2)]
        for player in players:
            table.add_player(player)

        table.deal_hole_cards()
        for player in players:
            assert len(player.hole_cards) == 2

    def test_set_current_player(self):
        """Test setting current player."""
        table = Table(6)
        assert table.current_player_seat is None
        table.set_current_player(3)
        assert table.current_player_seat == 3


class TestTableIntegration:
    """Integration tests for Table with multiple operations."""

    def test_full_table_setup(self):
        """Test setting up a full game scenario."""
        table = Table(6)
        players = [
            HumanPlayer("Alice", 0, 1000),
            AIPlayer("Bot1", 1, 1000, Difficulty.NOVICE),
            AIPlayer("Bot2", 2, 1000, Difficulty.INTERMEDIATE),
        ]
        for player in players:
            table.add_player(player)

        assert len(table.get_all_players()) == 3
        assert len(table.get_active_players()) == 3

        table.set_blinds(0, 1, 2)
        table.deal_hole_cards()

        for player in players:
            assert len(player.hole_cards) == 2

    def test_action_flow_scenario(self):
        """Test a realistic action flow."""
        table = Table(6)
        players = [Player("Player" + str(i), i, 1000) for i in range(3)]
        for player in players:
            table.add_player(player)

        # Set blinds
        table.set_blinds(0, 1, 2)

        # Deal cards
        table.deal_hole_cards()

        # Simulate some actions
        player1 = table.get_player(0)
        player1.remove_chips(100)
        table.add_to_pot(100)

        player2 = table.get_player(1)
        player2.remove_chips(50)
        table.add_to_pot(50)

        assert table.total_pot == 150
        assert player1.stack == 900
        assert player2.stack == 950


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
