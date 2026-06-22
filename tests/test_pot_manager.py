"""Unit tests for pot pooling and side pot management."""

import pytest
from src.poker.engine.pot_manager import Pot, PotManager
from src.poker.engine.hand_evaluator import Hand, HandType


def make_hand(hand_type: HandType, rank_value: int, kickers=None) -> Hand:
    """Create a Hand without real Card objects (sufficient for comparison)."""
    return Hand(hand_type, rank_value, kickers or [], [])


class TestPot:
    """Tests for the Pot dataclass."""

    def test_creation(self):
        pot = Pot(100, [0, 1, 2])
        assert pot.amount == 100
        assert pot.eligible_seats == [0, 1, 2]

    def test_repr(self):
        pot = Pot(50, [0, 1])
        assert "50" in repr(pot)
        assert "0" in repr(pot)


class TestPotManagerState:
    """Tests for PotManager initialization and reset."""

    def setup_method(self):
        self.pm = PotManager()

    def test_initial_state(self):
        assert self.pm.pots == []
        assert self.pm.get_total() == 0

    def test_repr(self):
        assert "PotManager" in repr(self.pm)

    def test_reset_clears_pots(self):
        self.pm.pots = [Pot(100, [0, 1])]
        self.pm.reset()
        assert self.pm.pots == []
        assert self.pm.get_total() == 0


class TestCalculatePots:
    """Tests for PotManager.calculate_pots."""

    def setup_method(self):
        self.pm = PotManager()

    def test_empty_contributions(self):
        self.pm.calculate_pots({})
        assert self.pm.pots == []

    def test_single_player(self):
        self.pm.calculate_pots({0: 200})
        assert len(self.pm.pots) == 1
        assert self.pm.pots[0].amount == 200
        assert self.pm.pots[0].eligible_seats == [0]

    def test_equal_contributions_one_pot(self):
        """No all-ins: single main pot with everyone eligible."""
        self.pm.calculate_pots({0: 100, 1: 100, 2: 100})
        assert len(self.pm.pots) == 1
        assert self.pm.pots[0].amount == 300
        assert set(self.pm.pots[0].eligible_seats) == {0, 1, 2}

    def test_one_all_in_two_pots(self):
        """One all-in player creates main pot + side pot."""
        # Player 0 all-in for 300, players 1 and 2 each contributed 600
        self.pm.calculate_pots({0: 300, 1: 600, 2: 600})
        assert len(self.pm.pots) == 2

        main = self.pm.pots[0]
        assert main.amount == 900  # 300 * 3
        assert set(main.eligible_seats) == {0, 1, 2}

        side = self.pm.pots[1]
        assert side.amount == 600  # 300 * 2
        assert set(side.eligible_seats) == {1, 2}

    def test_two_all_ins_three_pots(self):
        """Two all-ins at different stacks create three separate pots."""
        # Player 0: all-in 200, Player 1: all-in 500, Player 2: called 800
        self.pm.calculate_pots({0: 200, 1: 500, 2: 800})
        assert len(self.pm.pots) == 3

        assert self.pm.pots[0].amount == 600  # 200 * 3
        assert set(self.pm.pots[0].eligible_seats) == {0, 1, 2}

        assert self.pm.pots[1].amount == 600  # 300 * 2
        assert set(self.pm.pots[1].eligible_seats) == {1, 2}

        assert self.pm.pots[2].amount == 300  # 300 * 1
        assert set(self.pm.pots[2].eligible_seats) == {2}

    def test_total_equals_sum_of_contributions(self):
        contributions = {0: 200, 1: 500, 2: 800}
        self.pm.calculate_pots(contributions)
        assert self.pm.get_total() == sum(contributions.values())

    def test_uncalled_bet_isolated(self):
        """A player's excess that no one matched ends up in a solo pot."""
        self.pm.calculate_pots({0: 1000, 1: 500})
        assert len(self.pm.pots) == 2

        assert self.pm.pots[0].amount == 1000  # 500 * 2
        assert set(self.pm.pots[0].eligible_seats) == {0, 1}

        assert self.pm.pots[1].amount == 500  # 500 * 1 (excess, only player 0)
        assert self.pm.pots[1].eligible_seats == [0]

    def test_two_players_equal(self):
        self.pm.calculate_pots({0: 500, 1: 500})
        assert len(self.pm.pots) == 1
        assert self.pm.pots[0].amount == 1000
        assert set(self.pm.pots[0].eligible_seats) == {0, 1}


class TestAwardPots:
    """Tests for PotManager.award_pots."""

    def setup_method(self):
        self.pm = PotManager()
        self.high = make_hand(HandType.STRAIGHT_FLUSH, 9)
        self.mid = make_hand(HandType.FULL_HOUSE, 7)
        self.low = make_hand(HandType.ONE_PAIR, 2)

    def test_single_pot_clear_winner(self):
        self.pm.calculate_pots({0: 100, 1: 100, 2: 100})
        winnings = self.pm.award_pots({0: self.high, 1: self.mid, 2: self.low})
        assert winnings[0] == 300
        assert winnings[1] == 0
        assert winnings[2] == 0

    def test_two_way_tie_split_evenly(self):
        self.pm.calculate_pots({0: 100, 1: 100})
        tie = make_hand(HandType.FULL_HOUSE, 7)
        winnings = self.pm.award_pots({0: self.mid, 1: tie})
        assert winnings[0] == 100
        assert winnings[1] == 100

    def test_three_way_tie_odd_chip_to_lowest_seat(self):
        """Indivisible remainder chip goes to the lowest-numbered winner."""
        # Force a pot of 100 among 3 tied players (100 / 3 = 33 remainder 1)
        self.pm.pots = [Pot(100, [0, 1, 2])]
        tie = make_hand(HandType.HIGH_CARD, 14)
        winnings = self.pm.award_pots({0: tie, 1: tie, 2: tie})
        assert sum(winnings.values()) == 100
        assert winnings[0] == 34  # lowest seat gets the extra chip
        assert winnings[1] == 33
        assert winnings[2] == 33

    def test_all_in_player_cannot_win_side_pot(self):
        """Player 0 is all-in and wins the main pot but not the side pot."""
        self.pm.calculate_pots({0: 300, 1: 600, 2: 600})
        winnings = self.pm.award_pots({0: self.high, 1: self.mid, 2: self.low})
        assert winnings[0] == 900   # wins main pot (300 * 3)
        assert winnings[1] == 600   # wins side pot (best of 1 and 2)
        assert winnings[2] == 0

    def test_all_in_player_loses_main_pot(self):
        """All-in player with worst hand wins nothing."""
        self.pm.calculate_pots({0: 300, 1: 600, 2: 600})
        winnings = self.pm.award_pots({0: self.low, 1: self.high, 2: self.mid})
        assert winnings[0] == 0     # worst hand, wins nothing
        assert winnings[1] == 1500  # wins both pots
        assert winnings[2] == 0

    def test_uncalled_bet_returned_to_bettor(self):
        """Solo pot (uncalled bet) is awarded back to the only eligible player."""
        self.pm.calculate_pots({0: 1000, 1: 500})
        winnings = self.pm.award_pots({0: self.low, 1: self.high})
        assert winnings[1] == 1000  # wins the contested pot
        assert winnings[0] == 500   # uncalled bet returned

    def test_fold_leaves_single_winner(self):
        """If all but one player folds, that player wins every pot."""
        self.pm.calculate_pots({0: 100, 1: 100, 2: 100})
        winnings = self.pm.award_pots({0: self.low})  # only player 0 didn't fold
        assert winnings[0] == 300

    def test_two_player_all_in_winner_takes_all(self):
        self.pm.calculate_pots({0: 500, 1: 500})
        winnings = self.pm.award_pots({0: self.high, 1: self.low})
        assert winnings[0] == 1000
        assert winnings[1] == 0

    def test_empty_hands_returns_empty(self):
        self.pm.calculate_pots({0: 100, 1: 100})
        assert self.pm.award_pots({}) == {}

    def test_total_winnings_equals_total_pot(self):
        """Chips are conserved: total winnings always equals total in pots."""
        contributions = {0: 300, 1: 700, 2: 500}
        self.pm.calculate_pots(contributions)
        hands = {0: self.high, 1: self.mid, 2: self.low}
        winnings = self.pm.award_pots(hands)
        assert sum(winnings.values()) == self.pm.get_total()

    def test_side_pot_tie_between_eligible_players(self):
        """Tie in a side pot splits only between eligible players."""
        # Player 0 all-in 200, players 1 and 2 contributed 400 and tie
        self.pm.calculate_pots({0: 200, 1: 400, 2: 400})
        tie = make_hand(HandType.FLUSH, 10)
        winnings = self.pm.award_pots({0: self.low, 1: tie, 2: tie})
        assert winnings[0] == 0      # loses main pot
        assert winnings[1] == 500    # half of main (300) + half of side (400) — wait, let me recalculate

        # Main pot: 200 * 3 = 600, eligible 0,1,2. Player 0 has low, 1 and 2 tie → split 300 each
        # Side pot: 200 * 2 = 400, eligible 1,2. Tie → split 200 each
        assert winnings[0] == 0
        assert winnings[1] == 500    # 300 + 200
        assert winnings[2] == 500    # 300 + 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
