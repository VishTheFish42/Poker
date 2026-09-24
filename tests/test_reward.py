"""Unit tests for RL reward logic (Task 5.3), using results from real hands
played on the C++ engine rather than mocks, so the computed rewards are
checked against actual engine outcomes.
"""

import pytest

from poker_engine import ActionType
from src.poker.ai.reward import (
    BUST_PENALTY,
    RewardCalculator,
    STRONG_FOLD_PENALTY,
    WEAK_SHOWDOWN_LOSS_PENALTY,
    WEAK_SHOWDOWN_THRESHOLD,
    WIN_BONUS,
)
from tests.engine_helpers import act, cards, check_down, make_controller

BOARD = "2c 7h Qd Ks Ah"
BIG_BLIND = 10


def showdown(alice_hole, bob_hole, seat):
    """Heads-up hand (Alice seat 0, Bob seat 1, blinds 5/10) checked down
    on BOARD. Returns (seat's PlayerResult, is_showdown, its contribution,
    its stack afterwards)."""
    flop, turn, river = BOARD.split()[:3], BOARD.split()[3], BOARD.split()[4]
    deal = f"{alice_hole} {bob_hole} 8d {' '.join(flop)} 8h {turn} 8c {river}"
    gc = make_controller(num_players=2, sb=5, bb=BIG_BLIND, stacked_cards=cards(deal))
    check_down(gc)
    return _outcome(gc, seat)


def _outcome(gc, seat):
    result = gc.last_result
    player_result = next(r for r in result.player_results if r.seat == seat)
    return player_result, result.is_showdown, gc.contributions[seat], gc.table.get_player(seat).stack


class TestForResultWinner:
    def test_winner_reward_includes_net_chips_and_win_bonus(self):
        result, is_showdown, contribution, stack = showdown("As Ad", "2h 3d", seat=0)
        assert is_showdown and result.chips_won == 20

        reward = RewardCalculator.for_result(
            result, contribution=contribution, stack_after=stack, big_blind=BIG_BLIND, is_showdown=is_showdown
        )

        net = (result.chips_won - contribution) / BIG_BLIND
        assert reward == pytest.approx(net + WIN_BONUS)

    def test_uncontested_win_gets_bonus_too(self):
        gc = make_controller(num_players=2, sb=5, bb=BIG_BLIND)
        act(gc, ActionType.FOLD)  # button/SB folds, BB wins uncontested
        result, is_showdown, contribution, stack = _outcome(gc, seat=1)
        assert not is_showdown

        reward = RewardCalculator.for_result(
            result, contribution=contribution, stack_after=stack, big_blind=BIG_BLIND, is_showdown=is_showdown
        )

        net = (result.chips_won - contribution) / BIG_BLIND
        assert reward == pytest.approx(net + WIN_BONUS)


class TestForResultLoser:
    def test_losing_with_high_card_only_applies_weak_showdown_penalty(self):
        # Bob's hole cards don't pair or improve the board - his best hand off
        # this board is exactly high-card-ace (using the board's own ace).
        result, is_showdown, contribution, stack = showdown("As Ad", "4c 9s", seat=1)
        assert is_showdown
        assert result.best_hand.hand_type < WEAK_SHOWDOWN_THRESHOLD

        reward = RewardCalculator.for_result(
            result, contribution=contribution, stack_after=stack, big_blind=BIG_BLIND, is_showdown=is_showdown
        )

        assert result.chips_won == 0
        assert reward == pytest.approx(-contribution / BIG_BLIND + WEAK_SHOWDOWN_LOSS_PENALTY)

    def test_losing_with_a_decent_hand_gets_no_weak_penalty(self):
        # Bob makes two pair (kings and queens using the board) - not "weak".
        result, is_showdown, contribution, stack = showdown("As Ad", "Kc Qs", seat=1)

        reward = RewardCalculator.for_result(
            result, contribution=contribution, stack_after=stack, big_blind=BIG_BLIND, is_showdown=is_showdown
        )

        assert result.chips_won == 0
        assert reward == pytest.approx(-contribution / BIG_BLIND)

    def test_bust_applies_penalty(self):
        result, is_showdown, contribution, _ = showdown("As Ad", "4c 9s", seat=1)

        reward = RewardCalculator.for_result(
            result, contribution=contribution, stack_after=0, big_blind=BIG_BLIND, is_showdown=is_showdown
        )

        assert reward == pytest.approx(
            -contribution / BIG_BLIND + WEAK_SHOWDOWN_LOSS_PENALTY + BUST_PENALTY
        )


class TestForFold:
    def test_basic_fold_loses_contribution_only(self):
        reward = RewardCalculator.for_fold(contribution=30, stack_after=970, big_blind=10)
        assert reward == pytest.approx(-3.0)

    def test_fold_bust_applies_penalty(self):
        reward = RewardCalculator.for_fold(contribution=1000, stack_after=0, big_blind=10)
        assert reward == pytest.approx(-100.0 + BUST_PENALTY)

    def test_folding_a_strong_five_card_hand_is_penalized(self):
        hole = cards("Kc Ks")
        board = cards("Qh Qd 2c")

        reward = RewardCalculator.for_fold(
            contribution=20, stack_after=980, big_blind=10, hole_cards=hole, community_cards=board
        )

        assert reward == pytest.approx(-2.0 + STRONG_FOLD_PENALTY)

    def test_folding_a_weak_five_card_hand_is_not_penalized(self):
        hole = cards("2c 7s")
        board = cards("9h Jd 4c")

        reward = RewardCalculator.for_fold(
            contribution=20, stack_after=980, big_blind=10, hole_cards=hole, community_cards=board
        )

        assert reward == pytest.approx(-2.0)

    def test_preflop_fold_has_no_strength_penalty(self):
        hole = cards("Kc Ks")  # pocket kings, but unscoreable preflop

        reward = RewardCalculator.for_fold(
            contribution=10, stack_after=990, big_blind=10, hole_cards=hole, community_cards=[]
        )

        assert reward == pytest.approx(-1.0)


class TestFoldStrengthPenalty:
    def test_two_pair_is_strong(self):
        hole = cards("Kc Ks")
        board = cards("Qh Qd 2c")
        assert RewardCalculator.fold_strength_penalty(hole, board) == STRONG_FOLD_PENALTY

    def test_high_card_is_not_strong(self):
        hole = cards("2c 7s")
        board = cards("9h Jd 4c")
        assert RewardCalculator.fold_strength_penalty(hole, board) == 0.0

    def test_wrong_card_count_returns_zero(self):
        hole = cards("Kc Ks")
        assert RewardCalculator.fold_strength_penalty(hole, []) == 0.0  # preflop: 2 cards
        assert RewardCalculator.fold_strength_penalty(hole, cards(BOARD)[:4]) == 0.0  # turn: 6 cards
        assert RewardCalculator.fold_strength_penalty(hole, cards(BOARD)) == 0.0  # river: 7 cards

    def test_none_inputs_return_zero(self):
        assert RewardCalculator.fold_strength_penalty(None, None) == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
