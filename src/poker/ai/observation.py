"""Numeric observation encoding for RL-controlled players (Task 5.1).

Per specs/design.md's "Observation Space": turns a live `GameController`,
viewed from one seat, into a fixed-size numeric feature vector - hole and
community cards, own stack and pot contribution, pot size and call
amount, active opponent count and their stacks, the current betting
street, and position relative to the dealer button. Monetary quantities
are expressed in big blinds so the same policy network generalizes across
stake levels rather than overfitting to one buy-in size.
"""

from typing import List

import numpy as np

from ..engine.card import Card, CardSuit
from ..engine.controller import GameController
from ..engine.table import Table

CARD_FEATURES = 5  # normalized rank (1) + one-hot suit (4)
HOLE_CARD_SLOTS = 2
COMMUNITY_CARD_SLOTS = 5
SCALAR_COUNT = 6  # stack, contribution, pot, call amount, opponent count, relative position
STREET_COUNT = 5  # GameState.street_number: pre-flop, flop, turn, river, showdown
MAX_OPPONENTS = Table.MAX_PLAYERS - 1

_SUITS = list(CardSuit)


class ObservationEncoder:
    """Encodes a `GameController`'s state into a fixed-size feature vector."""

    @staticmethod
    def size() -> int:
        """Length of the encoded observation vector."""
        return (
            (HOLE_CARD_SLOTS + COMMUNITY_CARD_SLOTS) * CARD_FEATURES
            + SCALAR_COUNT
            + STREET_COUNT
            + MAX_OPPONENTS
        )

    @staticmethod
    def encode(controller: GameController, viewer_seat: int) -> np.ndarray:
        """Encode `controller`'s current state from `viewer_seat`'s perspective.

        Args:
            controller: The live game controller to observe.
            viewer_seat: Which seat's hole cards, stack, and position to
                encode. Only this seat's hole cards are included - a
                policy never gets to see other players' hands.

        Returns:
            A 1-D float32 array of length `size()`.
        """
        table = controller.table
        big_blind = max(controller.big_blind_amount, 1)
        player = table.get_player(viewer_seat)

        features: List[float] = []
        features.extend(_encode_cards(player.hole_cards if player else [], HOLE_CARD_SLOTS))
        features.extend(_encode_cards(table.community_cards, COMMUNITY_CARD_SLOTS))
        features.extend(_encode_scalars(controller, viewer_seat, big_blind))
        features.extend(_encode_street(table))
        features.extend(_encode_opponent_stacks(table, viewer_seat, big_blind))

        return np.array(features, dtype=np.float32)


def _encode_card(card: Card) -> List[float]:
    suit_one_hot = [1.0 if card.suit is suit else 0.0 for suit in _SUITS]
    return [card.rank.numeric_value / 14.0] + suit_one_hot


def _encode_cards(cards: List[Card], slots: int) -> List[float]:
    features: List[float] = []
    for index in range(slots):
        if index < len(cards):
            features.extend(_encode_card(cards[index]))
        else:
            features.extend([0.0] * CARD_FEATURES)
    return features


def _encode_scalars(controller: GameController, viewer_seat: int, big_blind: int) -> List[float]:
    table = controller.table
    player = table.get_player(viewer_seat)
    stack = player.stack if player else 0
    contribution = controller.total_contributions.get(viewer_seat, 0)
    call_amount = (
        controller.betting_round.get_amount_to_call(viewer_seat)
        if controller.betting_round is not None
        else 0
    )
    active_opponents = sum(1 for p in table.get_active_players() if p.seat != viewer_seat)
    num_seats = table.num_seats
    button = table.button_seat if table.button_seat is not None else 0
    relative_position = ((viewer_seat - button) % num_seats) / num_seats if num_seats else 0.0

    return [
        stack / big_blind,
        contribution / big_blind,
        table.total_pot / big_blind,
        call_amount / big_blind,
        active_opponents / max(num_seats - 1, 1),
        relative_position,
    ]


def _encode_street(table: Table) -> List[float]:
    one_hot = [0.0] * STREET_COUNT
    street_index = table.game_state.street_number
    if 0 <= street_index < STREET_COUNT:
        one_hot[street_index] = 1.0
    return one_hot


def _encode_opponent_stacks(table: Table, viewer_seat: int, big_blind: int) -> List[float]:
    stacks = [0.0] * MAX_OPPONENTS
    num_seats = table.num_seats
    for offset in range(1, num_seats):
        if offset - 1 >= MAX_OPPONENTS:
            break
        opponent = table.get_player((viewer_seat + offset) % num_seats)
        if opponent is not None:
            stacks[offset - 1] = opponent.stack / big_blind
    return stacks
