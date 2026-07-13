"""Unit tests for the main application window (Task 4.1) and its wiring to
the lobby/table screens (Task 4.2).
"""

import pytest
from PySide6.QtWidgets import QWidget

from src.poker.engine.player import Difficulty
from src.poker.ui.lobby_view import LobbySettings
from src.poker.ui.main_window import DEFAULT_WINDOW_TITLE, LOBBY_VIEW_NAME, TABLE_VIEW_NAME, MainWindow


class TestMainWindowInitialization:
    def test_window_title(self, qapp):
        window = MainWindow()
        assert window.windowTitle() == DEFAULT_WINDOW_TITLE

    def test_has_reasonable_default_size(self, qapp):
        window = MainWindow()
        assert window.width() >= 1024
        assert window.height() >= 768

    def test_starts_on_lobby_view(self, qapp):
        window = MainWindow()
        assert window.current_view_name == LOBBY_VIEW_NAME
        assert window.has_view(LOBBY_VIEW_NAME)

    def test_registers_table_view(self, qapp):
        window = MainWindow()
        assert window.has_view(TABLE_VIEW_NAME)

    def test_central_widget_is_a_stack(self, qapp):
        window = MainWindow()
        assert window.centralWidget() is not None


class TestViewManagement:
    def test_add_and_show_custom_view(self, qapp):
        window = MainWindow()
        placeholder = QWidget()
        window.add_view("custom", placeholder)

        window.show_view("custom")

        assert window.current_view_name == "custom"
        assert window.has_view("custom")

    def test_switch_between_lobby_and_table(self, qapp):
        window = MainWindow()

        window.show_view(TABLE_VIEW_NAME)
        assert window.current_view_name == TABLE_VIEW_NAME

        window.show_view(LOBBY_VIEW_NAME)
        assert window.current_view_name == LOBBY_VIEW_NAME

    def test_duplicate_view_name_raises(self, qapp):
        window = MainWindow()
        with pytest.raises(ValueError):
            window.add_view(LOBBY_VIEW_NAME, QWidget())

    def test_show_unregistered_view_raises(self, qapp):
        window = MainWindow()
        with pytest.raises(KeyError):
            window.show_view("nonexistent")

    def test_has_view_false_for_unregistered_name(self, qapp):
        window = MainWindow()
        assert not window.has_view("nonexistent")


class TestLobbyToTableFlow:
    """Task 4.2: starting a game from the lobby moves to the table screen."""

    def test_start_requested_switches_to_table_view(self, qapp):
        window = MainWindow()
        settings = LobbySettings(
            player_name="Alice",
            buy_in=1000,
            num_opponents=3,
            difficulty=Difficulty.INTERMEDIATE,
            small_blind=5,
            big_blind=10,
        )

        window.lobby_view.start_requested.emit(settings)

        assert window.current_view_name == TABLE_VIEW_NAME
        assert window.lobby_settings is settings

    def test_clicking_start_button_with_valid_input_switches_view(self, qapp):
        window = MainWindow()
        window.lobby_view.name_input.setText("Bob")

        window.lobby_view.start_button.click()

        assert window.current_view_name == TABLE_VIEW_NAME
        assert window.lobby_settings.player_name == "Bob"

    def test_clicking_start_button_with_invalid_input_stays_on_lobby(self, qapp):
        window = MainWindow()
        window.lobby_view.name_input.setText("")  # no name entered

        window.lobby_view.start_button.click()

        assert window.current_view_name == LOBBY_VIEW_NAME
        assert window.lobby_settings is None


class TestTableToLobbyRestart:
    """Task 4.6: the table's Restart control returns to the lobby."""

    def test_restart_requested_switches_to_lobby_view(self, qapp):
        window = MainWindow()
        window.lobby_view.name_input.setText("Alice")
        window.lobby_view.start_button.click()
        assert window.current_view_name == TABLE_VIEW_NAME

        window.table_view.restart_requested.emit()

        assert window.current_view_name == LOBBY_VIEW_NAME

    def test_restart_clears_stashed_lobby_settings(self, qapp):
        window = MainWindow()
        window.lobby_view.name_input.setText("Alice")
        window.lobby_view.start_button.click()
        assert window.lobby_settings is not None

        window.table_view.restart_button.click()

        assert window.lobby_settings is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
