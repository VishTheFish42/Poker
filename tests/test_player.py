"""Unit tests for player models."""

import pytest
from src.poker.engine.card import Card, CardRank, CardSuit
from src.poker.engine.player import (
    Player,
    HumanPlayer,
    AIPlayer,
    Seat,
    PlayerStatus,
    Difficulty,
)


class TestPlayer:
    """Test cases for the base Player class."""

    def test_player_initialization(self):
        """Test player initialization."""
        player = Player("Alice", 0, 1000)
        assert player.name == "Alice"
        assert player.seat == 0
        assert player.stack == 1000
        assert player.status == PlayerStatus.ACTIVE
        assert player.current_bet == 0
        assert player.hole_cards == []
        assert not player.is_human

    def test_receive_cards(self):
        """Test giving a player hole cards."""
        player = Player("Alice", 0, 1000)
        cards = [
            Card(CardSuit.HEARTS, CardRank.ACE),
            Card(CardSuit.DIAMONDS, CardRank.KING),
        ]
        player.receive_cards(cards)
        assert player.hole_cards == cards

    def test_receive_cards_wrong_count(self):
        """Test that receiving wrong number of cards raises error."""
        player = Player("Alice", 0, 1000)
        with pytest.raises(ValueError):
            player.receive_cards([Card(CardSuit.HEARTS, CardRank.ACE)])

    def test_discard_cards(self):
        """Test discarding hole cards."""
        player = Player("Alice", 0, 1000)
        cards = [
            Card(CardSuit.HEARTS, CardRank.ACE),
            Card(CardSuit.DIAMONDS, CardRank.KING),
        ]
        player.receive_cards(cards)
        player.discard_cards()
        assert player.hole_cards == []

    def test_add_chips(self):
        """Test adding chips to a player's stack."""
        player = Player("Alice", 0, 1000)
        player.add_chips(500)
        assert player.stack == 1500

    def test_remove_chips(self):
        """Test removing chips from a player's stack."""
        player = Player("Alice", 0, 1000)
        removed = player.remove_chips(250)
        assert removed == 250
        assert player.stack == 750
        assert player.current_bet == 250

    def test_remove_chips_more_than_available(self):
        """Test that removing more chips than available returns actual amount."""
        player = Player("Alice", 0, 500)
        removed = player.remove_chips(1000)
        assert removed == 500
        assert player.stack == 0

    def test_fold(self):
        """Test marking a player as folded."""
        player = Player("Alice", 0, 1000)
        player.fold()
        assert player.status == PlayerStatus.FOLDED
        assert not player.is_active()

    def test_all_in(self):
        """Test marking a player as all-in."""
        player = Player("Alice", 0, 1000)
        player.go_all_in()
        assert player.status == PlayerStatus.ALL_IN
        assert player.is_active()
        assert not player.can_act()

    def test_has_chips(self):
        """Test checking if a player has chips."""
        player = Player("Alice", 0, 1000)
        assert player.has_chips()
        player.stack = 0
        assert not player.has_chips()

    def test_is_active(self):
        """Test checking if player is active."""
        player = Player("Alice", 0, 1000)
        assert player.is_active()
        player.fold()
        assert not player.is_active()

    def test_reset_for_new_hand(self):
        """Test resetting a player for a new hand."""
        player = Player("Alice", 0, 1000)
        cards = [
            Card(CardSuit.HEARTS, CardRank.ACE),
            Card(CardSuit.DIAMONDS, CardRank.KING),
        ]
        player.receive_cards(cards)
        player.fold()
        player.current_bet = 50
        
        player.reset_for_new_hand()
        assert player.hole_cards == []
        assert player.status == PlayerStatus.ACTIVE
        assert player.current_bet == 0


class TestHumanPlayer:
    """Test cases for HumanPlayer."""

    def test_human_player_initialization(self):
        """Test human player initialization."""
        player = HumanPlayer("Alice", 0, 1000)
        assert player.is_human
        assert player.name == "Alice"
        assert player.pending_action is None
        assert player.action_required is False

    def test_set_action(self):
        """Test setting an action for a human player."""
        player = HumanPlayer("Alice", 0, 1000)
        player.action_required = True
        # Mock action object
        mock_action = {"type": "fold"}
        player.set_action(mock_action)
        assert player.pending_action == mock_action
        assert player.action_required is False

    def test_is_waiting_for_action(self):
        """Test checking if player is waiting for action."""
        player = HumanPlayer("Alice", 0, 1000)
        assert not player.is_waiting_for_action()
        player.action_required = True
        assert player.is_waiting_for_action()

    def test_get_action_no_action_set(self):
        """Test that getting action without setting one raises error."""
        player = HumanPlayer("Alice", 0, 1000)
        with pytest.raises(RuntimeError):
            player.get_action({})


class TestAIPlayer:
    """Test cases for AIPlayer."""

    def test_ai_player_initialization(self):
        """Test AI player initialization."""
        player = AIPlayer("Bot", 1, 1000, Difficulty.ADVANCED)
        assert not player.is_human
        assert player.name == "Bot"
        assert player.difficulty == Difficulty.ADVANCED
        assert player.ai_agent is None

    def test_ai_player_difficulty_levels(self):
        """Test different difficulty levels."""
        novice = AIPlayer("Bot1", 0, 1000, Difficulty.NOVICE)
        intermediate = AIPlayer("Bot2", 1, 1000, Difficulty.INTERMEDIATE)
        advanced = AIPlayer("Bot3", 2, 1000, Difficulty.ADVANCED)
        
        assert novice.difficulty == Difficulty.NOVICE
        assert intermediate.difficulty == Difficulty.INTERMEDIATE
        assert advanced.difficulty == Difficulty.ADVANCED

    def test_set_agent(self):
        """Test setting an agent for an AI player."""
        player = AIPlayer("Bot", 0, 1000)
        # Mock agent
        mock_agent = {"select_action": lambda gs, p: None}
        player.set_agent(mock_agent)
        assert player.ai_agent == mock_agent

    def test_get_action_no_agent(self):
        """Test that getting action without agent raises error."""
        player = AIPlayer("Bot", 0, 1000)
        with pytest.raises(RuntimeError):
            player.get_action({})


class TestSeat:
    """Test cases for Seat."""

    def test_seat_initialization(self):
        """Test seat initialization."""
        seat = Seat(0, 0.0)
        assert seat.seat_number == 0
        assert seat.position_angle == 0.0
        assert seat.player is None
        assert not seat.is_button
        assert not seat.is_small_blind
        assert not seat.is_big_blind

    def test_set_player(self):
        """Test placing a player in a seat."""
        seat = Seat(0, 0.0)
        player = Player("Alice", 0, 1000)
        seat.set_player(player)
        assert seat.player == player
        assert seat.is_occupied()

    def test_empty_seat(self):
        """Test that a seat can be emptied."""
        seat = Seat(0, 0.0)
        player = Player("Alice", 0, 1000)
        seat.set_player(player)
        assert seat.is_occupied()
        seat.set_player(None)
        assert not seat.is_occupied()

    def test_clear_blind_markers(self):
        """Test clearing blind and button markers."""
        seat = Seat(0, 0.0)
        seat.is_button = True
        seat.is_small_blind = True
        seat.is_big_blind = False
        
        seat.clear_blind_markers()
        assert not seat.is_button
        assert not seat.is_small_blind
        assert not seat.is_big_blind


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
