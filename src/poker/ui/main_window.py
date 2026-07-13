"""Main application window for the Poker desktop app.

Owns the top-level window and a QStackedWidget holding the app's screens
(lobby, table, ...), switching between them by name via add_view()/
show_view(). Registers the real lobby and table screens, wires the
lobby's "Start Game" button to switch to the table screen, and wires the
table's "Restart" button (Task 4.6) back to the lobby so settings can be
adjusted before starting again. Connecting the table screen to a live
GameController is Task 6.1 - for now, starting a game just carries the
collected LobbySettings through, without one, and restarting simply
discards them and returns to the lobby. Screen switches fade the newly
shown view in (Task 4.7's `poker.ui.effects.fade_in`).
"""

from typing import Dict, Optional

from PySide6.QtWidgets import QMainWindow, QStackedWidget, QWidget

from .effects import fade_in
from .lobby_view import LobbySettings, LobbyView
from .table_view import TableView

DEFAULT_WINDOW_TITLE = "Poker"
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 800
LOBBY_VIEW_NAME = "lobby"
TABLE_VIEW_NAME = "table"


class MainWindow(QMainWindow):
    """Top-level application window managing transitions between screens."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(DEFAULT_WINDOW_TITLE)
        self.resize(DEFAULT_WIDTH, DEFAULT_HEIGHT)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)
        self._views: Dict[str, QWidget] = {}
        self.lobby_settings: Optional[LobbySettings] = None

        self.lobby_view = LobbyView()
        self.table_view = TableView()
        self.add_view(LOBBY_VIEW_NAME, self.lobby_view)
        self.add_view(TABLE_VIEW_NAME, self.table_view)
        self.lobby_view.start_requested.connect(self._on_start_requested)
        self.table_view.restart_requested.connect(self._on_restart_requested)

        self.show_view(LOBBY_VIEW_NAME)

    def add_view(self, name: str, widget: QWidget) -> None:
        """Register a screen under `name` so it can later be shown by name.

        Args:
            name: Unique identifier for the view (e.g. "lobby", "table").
            widget: The screen's root widget.

        Raises:
            ValueError: If `name` is already registered.
        """
        if name in self._views:
            raise ValueError(f"A view named '{name}' is already registered.")
        self._views[name] = widget
        self._stack.addWidget(widget)

    def show_view(self, name: str) -> None:
        """Switch the window to display the view registered under `name`.

        Args:
            name: The view's registered name.

        Raises:
            KeyError: If no view is registered under that name.
        """
        if name not in self._views:
            raise KeyError(f"No view named '{name}' has been registered.")
        widget = self._views[name]
        if self._stack.currentWidget() is widget:
            return
        self._stack.setCurrentWidget(widget)
        fade_in(widget)

    def has_view(self, name: str) -> bool:
        """Check whether a view is registered under `name`."""
        return name in self._views

    @property
    def current_view_name(self) -> Optional[str]:
        """The name of the currently displayed view, or None if empty."""
        current = self._stack.currentWidget()
        for name, widget in self._views.items():
            if widget is current:
                return name
        return None

    def _on_start_requested(self, settings: LobbySettings) -> None:
        """Handle the lobby's "Start Game" button: stash the settings and
        move to the table screen. Does not create a Table/GameController -
        that live wiring is Task 6.1.
        """
        self.lobby_settings = settings
        self.show_view(TABLE_VIEW_NAME)

    def _on_restart_requested(self) -> None:
        """Handle the table's "Restart" button: discard the stashed
        settings and return to the lobby so they can be re-entered or
        adjusted before starting again. Tearing down a live
        Table/GameController on restart is Task 6.3's job.
        """
        self.lobby_settings = None
        self.show_view(LOBBY_VIEW_NAME)
