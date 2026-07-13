"""Unit tests for RL reward logic (Task 5.3), using real engine objects
(Player, Showdown, HandEvaluator) rather than mocks so the computed
rewards are checked against actual engine outcomes.
"""

import pytest

from src.poker.ai.reward import (
    BUST_PENALTY,
    RewardCalculator,
    STRONG_FOLD_PENALTY,
    WEAK_SHOWDOWN_LOSS_PENALTY,
    WIN_BONUS,
)
from src.poker.engine.card import Card, CardRank as R, CardSuit as S
from src.poker.engine.player import Player
from src.poker.engine.pot_manager import PotManager
from src.poker.engine.showdown import Showdown

BOARD = [
    Card(S.CLUBS, R.TWO),
    Card(S.HEARTS, R.SEVEN),
    Card(S.DIAMONDS, R.QUEEN),
    Card(S.SPADES, R.KING),
    Card(S.HEARTS, R.ACE),
]


def make_player(seat: int, name: str, hole, stack: int = 1000) -> Player:
    p = Player(name, seat, stack)
    p.hole_cards = hole
    return p


def result_for(seat: int, players, board, contributions):
    pm = PotManager()
    pm.calculate_pots(contributions)
    result = Showdown.resolve(players, board, pm)
    return next(r for r in result.player_results if r.seat == seat), result.is_showdown


class TestForResultWinner:
    def test_winner_reward_includes_net_chips_and_win_bonus(self):
        alice = make_player(0, "Alice", [Card(S.SPADES, R.ACE), Card(S.DIAMONDS, R.ACE)])
        bob = make_player(1, "Bob", [Card(S.HEARTS, R.TWO), Card(S.DIAMONDS, R.THREE)])
        result, is_showdown = result_for(0, [alice, bob], BOARD, {0: 100, 1: 100})

        reward = RewardCalculator.for_result(
            result, contribution=100, stack_after=alice.stack, big_blind=10, is_showdown=is_showdown
        )

        net = (result.chips_won - 100) / 10
        assert reward == pytest.approx(net + WIN_BONUS)

    def test_uncontested_win_gets_bonus_too(self):
        alice = make_player(0, "Alice", [Card(S.SPADES, R.TWO), Card(S.DIAMONDS, R.THREE)])
        result, is_showdown = result_for(0, [alice], [], {0: 100, 1: 100})
        assert not is_showdown

        reward = RewardCalculator.for_result(
            result, contribution=100, stack_after=alice.stack, big_blind=10, is_showdown=is_showdown
        )

        net = (result.chips_won - 100) / 10
        assert reward == pytest.approx(net + WIN_BONUS)


class TestForResultLoser:
    def test_losing_with_high_card_only_applies_weak_showdown_penalty(self):
        alice = make_player(0, "Alice", [Card(S.SPADES, R.ACE), Card(S.DIAMONDS, R.ACE)])
        # Bob's hole cards don't pair or improve the board - his best hand off
        # this board is exactly high-card-ace (using the board's own ace).
        bob = make_player(1, "Bob", [Card(S.CLUBS, R.FOUR), Card(S.SPADES, R.NINE)])
        result, is_showdown = result_for(1, [alice, bob], BOARD, {0: 100, 1: 100})
        assert is_showdown

        bob_result = result
        reward = RewardCalculator.for_result(
            bob_result, contribution=100, stack_after=bob.stack, big_blind=10, is_showdown=is_showdown
        )

        net = (bob_result.chips_won - 100) / 10
        assert bob_result.chips_won == 0
        assert reward == pytest.approx(net + WEAK_SHOWDOWN_LOSS_PENALTY)

    def test_losing_with_a_decent_hand_gets_no_weak_penalty(self):
        alice = make_player(0, "Alice", [Card(S.SPADES, R.ACE), Card(S.DIAMONDS, R.ACE)])
        # Bob makes two pair (kings and queens using the board) - not "weak".
        bob = make_player(1, "Bob", [Card(S.CLUBS, R.KING), Card(S.SPADES, R.QUEEN)])
        result, is_showdown = result_for(1, [alice, bob], BOARD, {0: 100, 1: 100})

        reward = RewardCalculator.for_result(
            result, contribution=100, stack_after=bob.stack, big_blind=10, is_showdown=is_showdown
        )

        net = (result.chips_won - 100) / 10
        assert reward == pytest.approx(net)

    def test_bust_applies_penalty(self):
        alice = make_player(0, "Alice", [Card(S.SPADES, R.ACE), Card(S.DIAMONDS, R.ACE)])
        bob = make_player(1, "Bob", [Card(S.CLUBS, R.FOUR), Card(S.SPADES, R.NINE)], stack=0)
        result, is_showdown = result_for(1, [alice, bob], BOARD, {0: 100, 1: 100})

        reward = RewardCalculator.for_result(
            result, contribution=100, stack_after=0, big_blind=10, is_showdown=is_showdown
        )

        net = (result.chips_won - 100) / 10
        assert reward == pytest.approx(net + WEAK_SHOWDOWN_LOSS_PENALTY + BUST_PENALTY)


class TestForFold:
    def test_basic_fold_loses_contribution_only(self):
        reward = RewardCalculator.for_fold(contribution=30, stack_after=970, big_blind=10)
        assert reward == pytest.approx(-3.0)

    def test_fold_bust_applies_penalty(self):
        reward = RewardCalculator.for_fold(contribution=1000, stack_after=0, big_blind=10)
        assert reward == pytest.approx(-100.0 + BUST_PENALTY)

    def test_folding_a_strong_five_card_hand_is_penalized(self):
        hole = [Card(S.CLUBS, R.KING), Card(S.SPADES, R.KING)]
        board = [Card(S.HEARTS, R.QUEEN), Card(S.DIAMONDS, R.QUEEN), Card(S.CLUBS, R.TWO)]

        reward = RewardCalculator.for_fold(
            contribution=20, stack_after=980, big_blind=10, hole_cards=hole, community_cards=board
        )

        assert reward == pytest.approx(-2.0 + STRONG_FOLD_PENALTY)

    def test_folding_a_weak_five_card_hand_is_not_penalized(self):
        hole = [Card(S.CLUBS, R.TWO), Card(S.SPADES, R.SEVEN)]
        board = [Card(S.HEARTS, R.NINE), Card(S.DIAMONDS, R.JACK), Card(S.CLUBS, R.FOUR)]

        reward = RewardCalculator.for_fold(
            contribution=20, stack_after=980, big_blind=10, hole_cards=hole, community_cards=board
        )

        assert reward == pytest.approx(-2.0)

    def test_preflop_fold_has_no_strength_penalty(self):
        hole = [Card(S.CLUBS, R.KING), Card(S.SPADES, R.KING)]  # pocket kings, but unscoreable preflop

        reward = RewardCalculator.for_fold(
            contribution=10, stack_after=990, big_blind=10, hole_cards=hole, community_cards=[]
        )

        assert reward == pytest.approx(-1.0)


class TestFoldStrengthPenalty:
    def test_two_pair_is_strong(self):
        hole = [Card(S.CLUBS, R.KING), Card(S.SPADES, R.KING)]
        board = [Card(S.HEARTS, R.QUEEN), Card(S.DIAMONDS, R.QUEEN), Card(S.CLUBS, R.TWO)]
        assert RewardCalculator.fold_strength_penalty(hole, board) == STRONG_FOLD_PENALTY

    def test_high_card_is_not_strong(self):
        hole = [Card(S.CLUBS, R.TWO), Card(S.SPADES, R.SEVEN)]
        board = [Card(S.HEARTS, R.NINE), Card(S.DIAMONDS, R.JACK), Card(S.CLUBS, R.FOUR)]
        assert RewardCalculator.fold_strength_penalty(hole, board) == 0.0

    def test_wrong_card_count_returns_zero(self):
        hole = [Card(S.CLUBS, R.KING), Card(S.SPADES, R.KING)]
        assert RewardCalculator.fold_strength_penalty(hole, []) == 0.0  # preflop: 2 cards
        assert RewardCalculator.fold_strength_penalty(hole, BOARD[:4]) == 0.0  # turn: 6 cards
        assert RewardCalculator.fold_strength_penalty(hole, BOARD) == 0.0  # river: 7 cards

    def test_none_inputs_return_zero(self):
        assert RewardCalculator.fold_strength_penalty(None, None) == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
