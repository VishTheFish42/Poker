"""Unit tests for the RL observation encoder (Task 5.1), using a real
GameController/Table (not mocks) so the encoded features are proven
against actual engine state.
"""

import pytest

from src.poker.ai.observation import (
    CARD_FEATURES,
    COMMUNITY_CARD_SLOTS,
    HOLE_CARD_SLOTS,
    MAX_OPPONENTS,
    ObservationEncoder,
)
from src.poker.engine.card import Card, CardRank as R, CardSuit as S
from src.poker.engine.controller import GameController
from src.poker.engine.player import Player
from src.poker.engine.table import Table


def make_controller(num_players=3, stack=1000, sb=1, bb=2):
    table = Table(num_players)
    for seat in range(num_players):
        table.add_player(Player(f"P{seat}", seat, stack))
    gc = GameController(table, sb, bb)
    gc.start_new_hand()
    return gc


class TestSize:
    def test_encoded_length_matches_declared_size(self):
        gc = make_controller()
        vector = ObservationEncoder.encode(gc, viewer_seat=0)
        assert vector.shape == (ObservationEncoder.size(),)


class TestCardEncoding:
    def test_own_hole_cards_encoded_at_the_front(self):
        gc = make_controller(num_players=2)
        seat = gc.get_current_player().seat
        gc.table.get_player(seat).hole_cards = [Card(S.SPADES, R.ACE), Card(S.HEARTS, R.KING)]

        vector = ObservationEncoder.encode(gc, viewer_seat=seat)

        assert vector[0] == pytest.approx(R.ACE.numeric_value / 14.0)
        spade_index = 1 + list(S).index(S.SPADES)
        assert vector[spade_index] == pytest.approx(1.0)

    def test_undealt_community_cards_are_zero(self):
        gc = make_controller(num_players=2)  # preflop: no community cards yet
        vector = ObservationEncoder.encode(gc, viewer_seat=0)

        community_start = HOLE_CARD_SLOTS * CARD_FEATURES
        community_block = vector[community_start : community_start + COMMUNITY_CARD_SLOTS * CARD_FEATURES]
        assert all(value == 0.0 for value in community_block)

    def test_dealt_flop_cards_are_encoded(self):
        gc = make_controller(num_players=2)
        gc.table.community_cards = [Card(S.CLUBS, R.TWO), Card(S.HEARTS, R.SEVEN), Card(S.DIAMONDS, R.QUEEN)]

        vector = ObservationEncoder.encode(gc, viewer_seat=0)

        community_start = HOLE_CARD_SLOTS * CARD_FEATURES
        first_flop_card_rank = vector[community_start]
        assert first_flop_card_rank == pytest.approx(R.TWO.numeric_value / 14.0)

    def test_viewer_sees_own_cards_not_another_seats(self):
        gc = make_controller(num_players=2)
        gc.table.get_player(0).hole_cards = [Card(S.SPADES, R.ACE), Card(S.HEARTS, R.KING)]
        gc.table.get_player(1).hole_cards = [Card(S.CLUBS, R.TWO), Card(S.DIAMONDS, R.THREE)]

        vector_for_seat_0 = ObservationEncoder.encode(gc, viewer_seat=0)

        own_cards_block = vector_for_seat_0[: HOLE_CARD_SLOTS * CARD_FEATURES]
        assert own_cards_block[0] == pytest.approx(R.ACE.numeric_value / 14.0)
        assert own_cards_block[0] != pytest.approx(R.TWO.numeric_value / 14.0)


class TestScalarFeatures:
    def test_stack_and_pot_scaled_by_big_blind(self):
        gc = make_controller(num_players=2, stack=1000, sb=5, bb=10)
        seat = gc.get_current_player().seat
        vector = ObservationEncoder.encode(gc, viewer_seat=seat)

        scalars_start = (HOLE_CARD_SLOTS + COMMUNITY_CARD_SLOTS) * CARD_FEATURES
        stack_feature = vector[scalars_start]
        expected_stack = gc.table.get_player(seat).stack / 10
        assert stack_feature == pytest.approx(expected_stack)

    def test_call_amount_reflects_amount_owed(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        seat = gc.get_current_player().seat  # button/SB owes the call preflop
        legal = gc.get_legal_actions()

        vector = ObservationEncoder.encode(gc, viewer_seat=seat)

        scalars_start = (HOLE_CARD_SLOTS + COMMUNITY_CARD_SLOTS) * CARD_FEATURES
        call_amount_feature = vector[scalars_start + 3]
        assert call_amount_feature == pytest.approx(legal["call_amount"] / 2)


class TestStreetEncoding:
    def test_preflop_street_one_hot(self):
        gc = make_controller(num_players=2)
        vector = ObservationEncoder.encode(gc, viewer_seat=0)

        street_start = (HOLE_CARD_SLOTS + COMMUNITY_CARD_SLOTS) * CARD_FEATURES + 6
        street_block = vector[street_start : street_start + 5]
        assert list(street_block) == [1.0, 0.0, 0.0, 0.0, 0.0]

    def test_flop_street_one_hot(self):
        gc = make_controller(num_players=2)
        gc.table.game_state = gc.table.game_state.__class__.FLOP
        vector = ObservationEncoder.encode(gc, viewer_seat=0)

        street_start = (HOLE_CARD_SLOTS + COMMUNITY_CARD_SLOTS) * CARD_FEATURES + 6
        street_block = vector[street_start : street_start + 5]
        assert list(street_block) == [0.0, 1.0, 0.0, 0.0, 0.0]


class TestOpponentStacks:
    def test_opponent_stacks_ordered_relative_to_viewer(self):
        gc = make_controller(num_players=3, stack=1000, sb=1, bb=2)
        gc.table.get_player(1).stack = 700
        gc.table.get_player(2).stack = 300

        vector = ObservationEncoder.encode(gc, viewer_seat=0)

        opponents_start = (
            (HOLE_CARD_SLOTS + COMMUNITY_CARD_SLOTS) * CARD_FEATURES + 6 + 5
        )
        assert vector[opponents_start] == pytest.approx(700 / 2)
        assert vector[opponents_start + 1] == pytest.approx(300 / 2)
        assert all(v == 0.0 for v in vector[opponents_start + 2 : opponents_start + MAX_OPPONENTS])

    def test_heads_up_pads_remaining_opponent_slots_with_zero(self):
        gc = make_controller(num_players=2)
        vector = ObservationEncoder.encode(gc, viewer_seat=0)

        opponents_start = (
            (HOLE_CARD_SLOTS + COMMUNITY_CARD_SLOTS) * CARD_FEATURES + 6 + 5
        )
        opponent_block = vector[opponents_start : opponents_start + MAX_OPPONENTS]
        assert opponent_block[0] > 0  # the one real opponent
        assert all(v == 0.0 for v in opponent_block[1:])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
