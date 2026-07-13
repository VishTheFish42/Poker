"""Unit tests for the result dialog (Task 4.2), using real engine
ShowdownResult objects (not mocks) to prove the UI correctly interprets
actual engine output.
"""

import pytest
from PySide6.QtWidgets import QLabel

from src.poker.engine.card import Card, CardRank as R, CardSuit as S
from src.poker.engine.player import Player
from src.poker.engine.pot_manager import PotManager
from src.poker.engine.showdown import Showdown
from src.poker.ui.result_dialog import ResultDialog

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


class TestShowdownResult:
    def test_title_is_showdown(self, qapp):
        alice = make_player(0, "Alice", [Card(S.SPADES, R.ACE), Card(S.DIAMONDS, R.ACE)])
        bob = make_player(1, "Bob", [Card(S.HEARTS, R.TWO), Card(S.DIAMONDS, R.THREE)])
        pm = PotManager()
        pm.calculate_pots({0: 100, 1: 100})
        result = Showdown.resolve([alice, bob], BOARD, pm)

        dialog = ResultDialog(result)

        assert dialog.windowTitle() == "Showdown"

    def test_winner_and_pot_shown(self, qapp):
        alice = make_player(0, "Alice", [Card(S.SPADES, R.ACE), Card(S.DIAMONDS, R.ACE)])
        bob = make_player(1, "Bob", [Card(S.HEARTS, R.TWO), Card(S.DIAMONDS, R.THREE)])
        pm = PotManager()
        pm.calculate_pots({0: 100, 1: 100})
        result = Showdown.resolve([alice, bob], BOARD, pm)

        dialog = ResultDialog(result)
        labels_text = " ".join(l.text() for l in dialog.findChildren(QLabel))

        assert "Alice" in labels_text
        assert "wins $200" in labels_text
        assert "Total pot: $200" in labels_text


class TestFoldWinResult:
    def test_title_is_hand_complete(self, qapp):
        alice = make_player(0, "Alice", [Card(S.SPADES, R.TWO), Card(S.DIAMONDS, R.THREE)])
        pm = PotManager()
        pm.calculate_pots({0: 100, 1: 100})
        result = Showdown.resolve([alice], [], pm)

        dialog = ResultDialog(result)

        assert dialog.windowTitle() == "Hand Complete"

    def test_uncontested_message_shown(self, qapp):
        alice = make_player(0, "Alice", [Card(S.SPADES, R.TWO), Card(S.DIAMONDS, R.THREE)])
        pm = PotManager()
        pm.calculate_pots({0: 100, 1: 100})
        result = Showdown.resolve([alice], [], pm)

        dialog = ResultDialog(result)
        labels_text = " ".join(l.text() for l in dialog.findChildren(QLabel))

        assert "Alice wins the pot uncontested ($200)" in labels_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
