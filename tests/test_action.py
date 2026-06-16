"""Unit tests for action types and handling."""

import pytest
from src.poker.engine.action import Action, ActionType


class TestActionType:
    """Test cases for ActionType enum."""

    def test_action_types_exist(self):
        """Test that all action types exist."""
        assert ActionType.FOLD
        assert ActionType.CHECK
        assert ActionType.CALL
        assert ActionType.BET
        assert ActionType.RAISE
        assert ActionType.ALL_IN

    def test_action_type_string(self):
        """Test action type string representation."""
        assert str(ActionType.FOLD) == "fold"
        assert str(ActionType.CHECK) == "check"
        assert str(ActionType.CALL) == "call"


class TestAction:
    """Test cases for Action class."""

    def test_fold_action(self):
        """Test creating a fold action."""
        action = Action(ActionType.FOLD, 2)
        assert action.action_type == ActionType.FOLD
        assert action.player_seat == 2
        assert action.amount == 0

    def test_check_action(self):
        """Test creating a check action."""
        action = Action(ActionType.CHECK, 3)
        assert action.action_type == ActionType.CHECK
        assert action.player_seat == 3
        assert action.amount == 0

    def test_call_action(self):
        """Test creating a call action."""
        action = Action(ActionType.CALL, 1, 50)
        assert action.action_type == ActionType.CALL
        assert action.player_seat == 1
        assert action.amount == 50

    def test_bet_action(self):
        """Test creating a bet action."""
        action = Action(ActionType.BET, 4, 100)
        assert action.action_type == ActionType.BET
        assert action.player_seat == 4
        assert action.amount == 100

    def test_raise_action(self):
        """Test creating a raise action."""
        action = Action(ActionType.RAISE, 0, 200)
        assert action.action_type == ActionType.RAISE
        assert action.player_seat == 0
        assert action.amount == 200

    def test_all_in_action(self):
        """Test creating an all-in action."""
        action = Action(ActionType.ALL_IN, 5, 500)
        assert action.action_type == ActionType.ALL_IN
        assert action.player_seat == 5
        assert action.amount == 500

    def test_fold_with_nonzero_amount_invalid(self):
        """Test that fold with non-zero amount is invalid."""
        with pytest.raises(ValueError):
            Action(ActionType.FOLD, 2, 100)

    def test_check_with_nonzero_amount_invalid(self):
        """Test that check with non-zero amount is invalid."""
        with pytest.raises(ValueError):
            Action(ActionType.CHECK, 3, 50)

    def test_bet_with_negative_amount_invalid(self):
        """Test that bet with negative amount is invalid."""
        with pytest.raises(ValueError):
            Action(ActionType.BET, 4, -100)

    def test_call_with_negative_amount_invalid(self):
        """Test that call with negative amount is invalid."""
        with pytest.raises(ValueError):
            Action(ActionType.CALL, 1, -50)

    def test_action_repr(self):
        """Test string representation of actions."""
        fold = Action(ActionType.FOLD, 2)
        assert "Seat 2" in repr(fold)
        assert "fold" in repr(fold)

        bet = Action(ActionType.BET, 4, 100)
        assert "Seat 4" in repr(bet)
        assert "$100" in repr(bet)

    def test_action_equality(self):
        """Test action equality comparison."""
        action1 = Action(ActionType.FOLD, 2)
        action2 = Action(ActionType.FOLD, 2)
        action3 = Action(ActionType.CHECK, 2)

        assert action1 == action2
        assert action1 != action3

    def test_action_inequality_different_amount(self):
        """Test action inequality with different amounts."""
        action1 = Action(ActionType.BET, 4, 100)
        action2 = Action(ActionType.BET, 4, 150)
        assert action1 != action2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
