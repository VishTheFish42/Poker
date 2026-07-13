"""Unit tests for the table screen's seat/board rendering (Task 4.3),
action controls (Task 4.4), and game log/status panel (Task 4.5), using
real engine objects (not mocks) to prove the UI correctly reflects actual
engine state.
"""

import pytest
from PySide6.QtWidgets import QFrame

from src.poker.engine.card import Card, CardRank as R, CardSuit as S
from src.poker.engine.controller import GameController
from src.poker.engine.player import HumanPlayer, Player, PlayerStatus
from src.poker.engine.table import Table
from src.poker.ui.table_view import ActionPanel, CardLabel, GameLogView, SeatWidget, TableView


def make_table(num_seats=4, stack=1000):
    table = Table(num_seats)
    for seat in range(num_seats):
        table.add_player(Player(f"Player{seat}", seat, stack))
    return table


def make_controller(num_players=3, stack=1000, sb=1, bb=2):
    table = Table(num_players)
    for seat in range(num_players):
        table.add_player(Player(f"Player{seat}", seat, stack))
    gc = GameController(table, sb, bb)
    gc.start_new_hand()
    return gc


class TestSkeletonRegions:
    def test_has_all_four_regions(self, qapp):
        view = TableView()
        assert isinstance(view.board_area, QFrame)
        assert isinstance(view.seats_area, QFrame)
        assert isinstance(view.action_area, QFrame)
        assert isinstance(view.log_area, QFrame)

    def test_regions_are_distinct_widgets(self, qapp):
        view = TableView()
        regions = {view.board_area, view.seats_area, view.action_area, view.log_area}
        assert len(regions) == 4

    def test_pot_label_shows_default_pot(self, qapp):
        view = TableView()
        assert "Pot" in view.pot_label.text()
        assert "$0" in view.pot_label.text()


class TestSeatPool:
    def test_default_seat_count_matches_table_default(self, qapp):
        view = TableView(num_seats=6)
        assert view.seats_area.num_seats == 6
        assert all(isinstance(w, SeatWidget) for w in view.seats_area.seat_widgets)

    def test_empty_seat_shows_placeholder(self, qapp):
        view = TableView(num_seats=2)
        widget = view.seats_area.seat_widgets[0]
        assert widget.name_label.text() == "Empty Seat"

    def test_update_from_table_resizes_seat_pool(self, qapp):
        view = TableView(num_seats=6)
        table = make_table(num_seats=3)
        view.update_from_table(table)
        assert view.seats_area.num_seats == 3


class TestSeatContent:
    def test_player_name_and_stack_shown(self, qapp):
        table = make_table(num_seats=3, stack=1500)
        view = TableView(num_seats=3)
        view.update_from_table(table)

        widget = view.seats_area.seat_widgets[0]
        assert "Player0" in widget.name_label.text()
        assert widget.stack_label.text() == "$1500"

    def test_current_bet_shown_when_positive(self, qapp):
        table = make_table(num_seats=2)
        table.get_player(0).current_bet = 50
        view = TableView(num_seats=2)
        view.update_from_table(table)

        assert view.seats_area.seat_widgets[0].bet_label.text() == "Bet: $50"
        assert view.seats_area.seat_widgets[1].bet_label.text() == ""

    def test_folded_player_labeled_and_cards_hidden(self, qapp):
        table = make_table(num_seats=2)
        player = table.get_player(0)
        player.receive_cards([Card(S.SPADES, R.ACE), Card(S.HEARTS, R.KING)])
        player.fold()
        view = TableView(num_seats=2)
        view.update_from_table(table, viewer_seat=0)

        widget = view.seats_area.seat_widgets[0]
        assert "Folded" in widget.name_label.text()
        assert all(label.state == "empty" for label in widget.card_labels)

    def test_dealer_and_blind_markers_shown(self, qapp):
        table = make_table(num_seats=3)
        table.set_blinds(button_seat=0, small_blind_amount=5, big_blind_amount=10)
        view = TableView(num_seats=3)
        view.update_from_table(table)

        assert "D" in view.seats_area.seat_widgets[0].marker_label.text()
        assert "SB" in view.seats_area.seat_widgets[1].marker_label.text()
        assert "BB" in view.seats_area.seat_widgets[2].marker_label.text()

    def test_current_to_act_seat_is_highlighted(self, qapp):
        table = make_table(num_seats=2)
        table.set_current_player(1)
        view = TableView(num_seats=2)
        view.update_from_table(table)

        active_style = view.seats_area.seat_widgets[1].styleSheet()
        inactive_style = view.seats_area.seat_widgets[0].styleSheet()
        assert active_style != inactive_style
        assert "2ecc71" in active_style  # active border color
        assert "2ecc71" not in inactive_style


class TestHoleCardVisibility:
    def test_viewer_seat_cards_revealed(self, qapp):
        table = make_table(num_seats=2)
        cards = [Card(S.SPADES, R.ACE), Card(S.HEARTS, R.KING)]
        table.get_player(0).receive_cards(cards)
        view = TableView(num_seats=2)
        view.update_from_table(table, viewer_seat=0)

        widget = view.seats_area.seat_widgets[0]
        assert widget.card_labels[0].state == "face"
        assert widget.card_labels[0].text() == repr(cards[0])

    def test_other_seat_cards_hidden(self, qapp):
        table = make_table(num_seats=2)
        table.get_player(1).receive_cards(
            [Card(S.CLUBS, R.TWO), Card(S.DIAMONDS, R.THREE)]
        )
        view = TableView(num_seats=2)
        view.update_from_table(table, viewer_seat=0)

        widget = view.seats_area.seat_widgets[1]
        assert widget.card_labels[0].state == "back"
        assert widget.card_labels[0].text() == ""

    def test_no_viewer_seat_hides_everyone(self, qapp):
        table = make_table(num_seats=2)
        table.get_player(0).receive_cards(
            [Card(S.CLUBS, R.TWO), Card(S.DIAMONDS, R.THREE)]
        )
        view = TableView(num_seats=2)
        view.update_from_table(table, viewer_seat=None)

        assert view.seats_area.seat_widgets[0].card_labels[0].state == "back"


class TestCommunityCards:
    def test_dealt_cards_shown_and_rest_empty(self, qapp):
        table = make_table(num_seats=2)
        table.community_cards = [
            Card(S.CLUBS, R.TWO),
            Card(S.HEARTS, R.SEVEN),
            Card(S.DIAMONDS, R.QUEEN),
        ]
        view = TableView(num_seats=2)
        view.update_from_table(table)

        states = [label.state for label in view.community_cards]
        assert states == ["face", "face", "face", "empty", "empty"]
        assert view.community_cards[0].text() == repr(table.community_cards[0])

    def test_pot_amount_reflected(self, qapp):
        table = make_table(num_seats=2)
        table.set_pot(275)
        view = TableView(num_seats=2)
        view.update_from_table(table)

        assert view.pot_label.text() == "Pot: $275"


class TestPolishAnimationTriggers:
    """Task 4.7: reveal/highlight/pot animations should fire once per real
    change, not on every redraw of unchanged state.
    """

    def _spy_fade_in(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            "src.poker.ui.table_view.fade_in", lambda widget, *a, **k: calls.append(widget)
        )
        return calls

    def test_card_reveal_animates_once_for_the_same_card(self, qapp, monkeypatch):
        calls = self._spy_fade_in(monkeypatch)
        label = CardLabel()
        card = Card(S.SPADES, R.ACE)

        label.set_card(card)
        label.set_card(card)  # redraw of the same reveal - no new animation

        assert calls == [label]

    def test_card_reveal_animates_again_for_a_different_card(self, qapp, monkeypatch):
        calls = self._spy_fade_in(monkeypatch)
        label = CardLabel()

        label.set_card(Card(S.SPADES, R.ACE))
        label.set_card(Card(S.HEARTS, R.KING))

        assert calls == [label, label]

    def test_seat_activation_animates_once_while_staying_active(self, qapp, monkeypatch):
        calls = self._spy_fade_in(monkeypatch)
        table = make_table(num_seats=2)
        table.set_current_player(0)
        view = TableView(num_seats=2)

        view.update_from_table(table)
        view.update_from_table(table)  # still seat 0's turn

        seat0 = view.seats_area.seat_widgets[0]
        assert calls.count(seat0) == 1

    def test_pot_animates_only_when_it_changes(self, qapp, monkeypatch):
        calls = self._spy_fade_in(monkeypatch)
        table = make_table(num_seats=2)
        table.set_pot(50)
        view = TableView(num_seats=2)

        view.update_from_table(table)
        view.update_from_table(table)  # unchanged pot
        assert calls.count(view.pot_label) == 1

        table.set_pot(75)
        view.update_from_table(table)
        assert calls.count(view.pot_label) == 2


class TestActionPanelInitialState:
    def test_all_controls_start_disabled(self, qapp):
        panel = ActionPanel()
        assert not panel.fold_button.isEnabled()
        assert not panel.check_call_button.isEnabled()
        assert not panel.bet_raise_button.isEnabled()
        assert not panel.all_in_button.isEnabled()
        assert not panel.amount_input.isEnabled()


class TestActionPanelLegalActions:
    def test_preflop_big_blind_option_shows_check_and_raise(self, qapp):
        # 3-handed: seat 0 button/SB, seat 1 BB, seat 2 acts first preflop
        # and folds/calls so the action gets back around to the BB's option.
        gc = make_controller(num_players=3, sb=1, bb=2)
        gc.fold()  # seat 2 (UTG)
        gc.check_or_call()  # seat 0 (button/SB) calls
        legal = gc.get_legal_actions()

        panel = ActionPanel()
        panel.update_legal_actions(legal)

        assert panel.fold_button.isEnabled()
        assert panel.check_call_button.isEnabled()
        assert panel.check_call_button.text() == "Check"
        assert panel.bet_raise_button.isEnabled() == legal["can_raise"]
        if legal["can_raise"]:
            assert panel.bet_raise_button.text() == "Raise"
            assert panel.amount_input.minimum() == legal["min_raise"]
            assert panel.amount_input.maximum() == legal["max_raise"]

    def test_facing_a_bet_shows_call_amount_and_raise(self, qapp):
        gc = make_controller(num_players=2, sb=1, bb=2)
        legal = gc.get_legal_actions()  # heads-up: button/SB owes the call

        panel = ActionPanel()
        panel.update_legal_actions(legal)

        assert legal["can_call"] and not legal["can_check"]
        assert panel.check_call_button.text() == f"Call ${legal['call_amount']}"
        assert panel.bet_raise_button.text() == "Raise"
        assert panel.all_in_button.isEnabled()

    def test_opening_action_shows_bet_not_raise(self, qapp):
        gc = make_controller(num_players=2, sb=1, bb=2)
        gc.check_or_call()  # SB calls
        gc.check_or_call()  # BB checks their option -> flop, no bet yet
        legal = gc.get_legal_actions()

        panel = ActionPanel()
        panel.update_legal_actions(legal)

        assert legal["can_bet"]
        assert panel.bet_raise_button.text() == "Bet"
        assert panel.amount_input.minimum() == legal["min_bet"]
        assert panel.amount_input.maximum() == legal["max_bet"]

    def test_disable_all_resets_labels(self, qapp):
        gc = make_controller(num_players=2, sb=1, bb=2)
        panel = ActionPanel()
        panel.update_legal_actions(gc.get_legal_actions())

        panel.disable_all()

        assert not panel.fold_button.isEnabled()
        assert not panel.check_call_button.isEnabled()
        assert not panel.bet_raise_button.isEnabled()
        assert not panel.all_in_button.isEnabled()
        assert panel.check_call_button.text() == "Check"
        assert panel.bet_raise_button.text() == "Bet"


class TestActionPanelSignals:
    def test_fold_button_emits_signal(self, qapp):
        panel = ActionPanel()
        panel.update_legal_actions(make_controller(2).get_legal_actions())
        received = []
        panel.fold_requested.connect(lambda: received.append(True))

        panel.fold_button.click()

        assert received == [True]

    def test_check_call_button_emits_signal(self, qapp):
        panel = ActionPanel()
        panel.update_legal_actions(make_controller(2).get_legal_actions())
        received = []
        panel.check_call_requested.connect(lambda: received.append(True))

        panel.check_call_button.click()

        assert received == [True]

    def test_bet_raise_button_emits_bet_with_amount_when_opening(self, qapp):
        gc = make_controller(num_players=2, sb=1, bb=2)
        gc.check_or_call()
        gc.check_or_call()  # reach the flop with no bet yet -> "Bet" mode
        panel = ActionPanel()
        panel.update_legal_actions(gc.get_legal_actions())
        received = []
        panel.bet_requested.connect(lambda amount: received.append(amount))

        panel.bet_raise_button.click()

        assert received == [panel.amount_input.value()]

    def test_bet_raise_button_emits_raise_with_amount_when_facing_a_bet(self, qapp):
        gc = make_controller(num_players=2, sb=1, bb=2)
        panel = ActionPanel()
        panel.update_legal_actions(gc.get_legal_actions())
        received = []
        panel.raise_requested.connect(lambda amount: received.append(amount))

        panel.bet_raise_button.click()

        assert received == [panel.amount_input.value()]

    def test_all_in_button_emits_signal(self, qapp):
        panel = ActionPanel()
        panel.update_legal_actions(make_controller(2).get_legal_actions())
        received = []
        panel.all_in_requested.connect(lambda: received.append(True))

        panel.all_in_button.click()

        assert received == [True]


class TestTableViewActionArea:
    def test_action_area_is_action_panel(self, qapp):
        view = TableView()
        assert isinstance(view.action_area, ActionPanel)


class TestGameLogViewStatus:
    def test_status_shows_action_prompt(self, qapp):
        gc = make_controller(num_players=2, sb=1, bb=2)
        log_view = GameLogView()

        log_view.set_status(gc.get_action_prompt())

        assert "turn" in log_view.status_label.text()

    def test_status_clears_when_no_one_is_on_the_clock(self, qapp):
        log_view = GameLogView()
        log_view.set_status("Alice's turn.")

        log_view.set_status(None)

        assert log_view.status_label.text() == ""


class TestGameLogViewLog:
    def test_set_log_populates_all_lines(self, qapp):
        gc = make_controller(num_players=2, sb=1, bb=2)
        gc.fold()  # ends the hand and logs blind posts + the fold + result
        log_view = GameLogView()

        log_view.set_log(gc.log)

        assert log_view.log_list.count() == len(gc.log)
        assert log_view.log_list.item(0).text() == gc.log[0]
        assert log_view.log_list.item(log_view.log_list.count() - 1).text() == gc.log[-1]

    def test_set_log_replaces_previous_contents(self, qapp):
        log_view = GameLogView()
        log_view.set_log(["first message"])

        log_view.set_log(["second message"])

        assert log_view.log_list.count() == 1
        assert log_view.log_list.item(0).text() == "second message"

    def test_append_message_adds_without_clearing(self, qapp):
        log_view = GameLogView()
        log_view.set_log(["first message"])

        log_view.append_message("second message")

        assert log_view.log_list.count() == 2
        assert log_view.log_list.item(1).text() == "second message"


class TestTableViewLogArea:
    def test_log_area_is_game_log_view(self, qapp):
        view = TableView()
        assert isinstance(view.log_area, GameLogView)


class TestTableViewRestart:
    def test_restart_button_emits_signal(self, qapp):
        view = TableView()
        received = []
        view.restart_requested.connect(lambda: received.append(True))

        view.restart_button.click()

        assert received == [True]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
