"""Unit tests for the RL observation encoder (Task 5.1), using the real C++
engine (not mocks) so the encoded features are proven against actual
engine state.
"""

import pytest

from poker_engine import Suit
from src.poker.ai.observation import (
    CARD_FEATURES,
    COMMUNITY_CARD_SLOTS,
    HOLE_CARD_SLOTS,
    MAX_OPPONENTS,
    ObservationEncoder,
)
from tests.engine_helpers import cards, check_or_call, make_controller

SCALARS_START = (HOLE_CARD_SLOTS + COMMUNITY_CARD_SLOTS) * CARD_FEATURES
STREET_START = SCALARS_START + 6
OPPONENTS_START = STREET_START + 5
SUIT_ORDER = list(Suit.__members__.values())

# Heads-up: seat 0 As Kh, seat 1 2c 3d, burn, flop 2d 7h Qc.
HEADS_UP_DEAL = cards("As Kh 2c 3d 8s 2d 7h Qc")


class TestSize:
    def test_encoded_length_matches_declared_size(self):
        gc = make_controller()
        vector = ObservationEncoder.encode(gc, viewer_seat=0)
        assert vector.shape == (ObservationEncoder.size(),)


class TestCardEncoding:
    def test_own_hole_cards_encoded_at_the_front(self):
        gc = make_controller(num_players=2, stacked_cards=HEADS_UP_DEAL)

        vector = ObservationEncoder.encode(gc, viewer_seat=0)

        assert vector[0] == pytest.approx(14 / 14.0)  # ace
        spade_index = 1 + SUIT_ORDER.index(Suit.SPADES)
        assert vector[spade_index] == pytest.approx(1.0)
        assert sum(vector[1 : 1 + 4]) == pytest.approx(1.0)  # exactly one suit set

    def test_undealt_community_cards_are_zero(self):
        gc = make_controller(num_players=2)  # preflop: no community cards yet
        vector = ObservationEncoder.encode(gc, viewer_seat=0)

        community_start = HOLE_CARD_SLOTS * CARD_FEATURES
        community_block = vector[community_start : community_start + COMMUNITY_CARD_SLOTS * CARD_FEATURES]
        assert all(value == 0.0 for value in community_block)

    def test_dealt_flop_cards_are_encoded(self):
        gc = make_controller(num_players=2, stacked_cards=HEADS_UP_DEAL)
        check_or_call(gc)
        check_or_call(gc)  # flop: 2d 7h Qc

        vector = ObservationEncoder.encode(gc, viewer_seat=0)

        community_start = HOLE_CARD_SLOTS * CARD_FEATURES
        assert vector[community_start] == pytest.approx(2 / 14.0)
        assert vector[community_start + CARD_FEATURES] == pytest.approx(7 / 14.0)
        assert vector[community_start + 2 * CARD_FEATURES] == pytest.approx(12 / 14.0)
        assert vector[community_start + 3 * CARD_FEATURES] == 0.0  # turn not dealt yet

    def test_viewer_sees_own_cards_not_another_seats(self):
        gc = make_controller(num_players=2, stacked_cards=HEADS_UP_DEAL)

        seat_0_view = ObservationEncoder.encode(gc, viewer_seat=0)
        seat_1_view = ObservationEncoder.encode(gc, viewer_seat=1)

        assert seat_0_view[0] == pytest.approx(14 / 14.0)  # own ace, not seat 1's two
        assert seat_1_view[0] == pytest.approx(2 / 14.0)


class TestScalarFeatures:
    def test_stack_and_pot_scaled_by_big_blind(self):
        gc = make_controller(num_players=2, stack=1000, sb=5, bb=10)
        seat = gc.current_seat
        vector = ObservationEncoder.encode(gc, viewer_seat=seat)

        assert vector[SCALARS_START] == pytest.approx(gc.table.get_player(seat).stack / 10)
        assert vector[SCALARS_START + 2] == pytest.approx(15 / 10)  # pot: both blinds

    def test_contribution_reflects_chips_put_in_this_hand(self):
        gc = make_controller(num_players=2, sb=5, bb=10)  # seat 0 posted the SB
        vector = ObservationEncoder.encode(gc, viewer_seat=0)
        assert vector[SCALARS_START + 1] == pytest.approx(5 / 10)

    def test_call_amount_reflects_amount_owed(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        seat = gc.current_seat  # button/SB owes the call preflop
        legal = gc.legal_actions()

        vector = ObservationEncoder.encode(gc, viewer_seat=seat)

        assert vector[SCALARS_START + 3] == pytest.approx(legal.call_amount / 2)


class TestStreetEncoding:
    def test_preflop_street_one_hot(self):
        gc = make_controller(num_players=2)
        vector = ObservationEncoder.encode(gc, viewer_seat=0)
        assert list(vector[STREET_START : STREET_START + 5]) == [1.0, 0.0, 0.0, 0.0, 0.0]

    def test_flop_street_one_hot(self):
        gc = make_controller(num_players=2)
        check_or_call(gc)
        check_or_call(gc)
        vector = ObservationEncoder.encode(gc, viewer_seat=0)
        assert list(vector[STREET_START : STREET_START + 5]) == [0.0, 1.0, 0.0, 0.0, 0.0]


class TestOpponentStacks:
    def test_opponent_stacks_ordered_relative_to_viewer(self):
        gc = make_controller(stacks=[1000, 700, 300], sb=1, bb=2)  # seats 1 and 2 posted 1 and 2

        vector = ObservationEncoder.encode(gc, viewer_seat=0)

        assert vector[OPPONENTS_START] == pytest.approx(699 / 2)
        assert vector[OPPONENTS_START + 1] == pytest.approx(298 / 2)
        assert all(v == 0.0 for v in vector[OPPONENTS_START + 2 : OPPONENTS_START + MAX_OPPONENTS])

    def test_heads_up_pads_remaining_opponent_slots_with_zero(self):
        gc = make_controller(num_players=2)
        vector = ObservationEncoder.encode(gc, viewer_seat=0)

        opponent_block = vector[OPPONENTS_START : OPPONENTS_START + MAX_OPPONENTS]
        assert opponent_block[0] > 0  # the one real opponent
        assert all(v == 0.0 for v in opponent_block[1:])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
