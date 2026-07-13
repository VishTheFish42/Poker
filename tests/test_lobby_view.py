"""Unit tests for the lobby screen (Task 4.2)."""

import pytest

from src.poker.engine.player import Difficulty
from src.poker.ui.lobby_view import LobbySettings, LobbyView


class TestDefaults:
    def test_default_settings_are_valid(self, qapp):
        view = LobbyView()
        view.name_input.setText("Alice")
        settings = view.get_settings()
        assert view.validate(settings) == ""

    def test_default_difficulty_is_intermediate(self, qapp):
        view = LobbyView()
        assert view.get_settings().difficulty == Difficulty.INTERMEDIATE

    def test_opponent_count_is_capped_at_nine(self, qapp):
        view = LobbyView()
        view.opponents_input.setValue(50)
        assert view.get_settings().num_opponents == 9


class TestValidation:
    def test_empty_name_is_invalid(self, qapp):
        view = LobbyView()
        view.name_input.setText("   ")  # whitespace only
        settings = view.get_settings()
        assert view.validate(settings) != ""
        assert settings.player_name == ""  # stripped

    def test_big_blind_below_small_blind_is_invalid(self, qapp):
        view = LobbyView()
        view.name_input.setText("Alice")
        view.small_blind_input.setValue(20)
        view.big_blind_input.setValue(10)
        settings = view.get_settings()
        assert view.validate(settings) != ""

    def test_buy_in_below_big_blind_is_invalid(self, qapp):
        view = LobbyView()
        view.name_input.setText("Alice")
        view.buy_in_input.setValue(100)
        view.big_blind_input.setValue(500)
        settings = view.get_settings()
        assert view.validate(settings) != ""


class TestStartButton:
    def test_valid_input_emits_start_requested(self, qapp):
        view = LobbyView()
        view.name_input.setText("Alice")

        received = []
        view.start_requested.connect(received.append)
        view.start_button.click()

        assert len(received) == 1
        assert isinstance(received[0], LobbySettings)
        assert received[0].player_name == "Alice"

    def test_invalid_input_does_not_emit_and_shows_error(self, qapp):
        view = LobbyView()
        view.show()  # isVisible() requires the widget to actually be shown
        view.name_input.setText("")

        received = []
        view.start_requested.connect(received.append)
        view.start_button.click()

        assert received == []
        assert view.error_label.isVisible()
        assert view.error_label.text() != ""

    def test_settings_reflect_all_fields(self, qapp):
        view = LobbyView()
        view.name_input.setText("Carol")
        view.buy_in_input.setValue(2000)
        view.opponents_input.setValue(5)
        view.small_blind_input.setValue(25)
        view.big_blind_input.setValue(50)

        received = []
        view.start_requested.connect(received.append)
        view.start_button.click()

        settings = received[0]
        assert settings.player_name == "Carol"
        assert settings.buy_in == 2000
        assert settings.num_opponents == 5
        assert settings.small_blind == 25
        assert settings.big_blind == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
