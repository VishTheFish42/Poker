"""Lobby screen: collects player name, buy-in, opponent count, and
difficulty before a game starts.

Per design.md this screen's job is just to gather setup input and hand it
off - it does not create a Table/GameController itself (that wiring is
Task 6.1's job). It only validates the input and emits `start_requested`
with the collected settings.
"""

from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..engine.player import Difficulty

MIN_BUY_IN = 100
MAX_BUY_IN = 1_000_000
DEFAULT_BUY_IN = 1000

MIN_OPPONENTS = 1
MAX_OPPONENTS = 9  # table seats max at 10 total: 1 human + up to 9 opponents

MIN_BLIND = 1
MAX_BLIND = 1_000_000
DEFAULT_SMALL_BLIND = 5
DEFAULT_BIG_BLIND = 10

DIFFICULTY_LABELS = {
    Difficulty.NOVICE: "Novice",
    Difficulty.INTERMEDIATE: "Intermediate",
    Difficulty.ADVANCED: "Advanced",
}


@dataclass
class LobbySettings:
    """The settings collected from the lobby screen when starting a game."""

    player_name: str
    buy_in: int
    num_opponents: int
    difficulty: Difficulty
    small_blind: int
    big_blind: int


class LobbyView(QWidget):
    """Start screen: player name, buy-in, opponent count, blinds, difficulty."""

    start_requested = Signal(object)  # emits a LobbySettings

    def __init__(self) -> None:
        super().__init__()

        self.name_input = self._make_name_input()
        self.buy_in_input = self._make_spinbox(MIN_BUY_IN, MAX_BUY_IN, DEFAULT_BUY_IN, step=100)
        self.opponents_input = self._make_spinbox(MIN_OPPONENTS, MAX_OPPONENTS, 3)
        self.small_blind_input = self._make_spinbox(
            MIN_BLIND, MAX_BLIND, DEFAULT_SMALL_BLIND, step=5
        )
        self.big_blind_input = self._make_spinbox(MIN_BLIND, MAX_BLIND, DEFAULT_BIG_BLIND, step=5)
        self.difficulty_input = self._make_difficulty_combo()

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #c0392b;")
        self.error_label.setVisible(False)

        self.start_button = QPushButton("Start Game")
        self.start_button.clicked.connect(self._on_start_clicked)

        self._build_layout()

    def _make_name_input(self) -> QLineEdit:
        field = QLineEdit()
        field.setPlaceholderText("Enter your name")
        return field

    def _make_spinbox(self, minimum: int, maximum: int, default: int, step: int = 1) -> QSpinBox:
        box = QSpinBox()
        box.setRange(minimum, maximum)
        box.setSingleStep(step)
        box.setValue(default)
        return box

    def _make_difficulty_combo(self) -> QComboBox:
        combo = QComboBox()
        for difficulty, label in DIFFICULTY_LABELS.items():
            combo.addItem(label, difficulty)
        combo.setCurrentIndex(list(DIFFICULTY_LABELS).index(Difficulty.INTERMEDIATE))
        return combo

    def _build_layout(self) -> None:
        title = QLabel("Texas Hold'em")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")

        form = QFormLayout()
        form.addRow("Player name:", self.name_input)
        form.addRow("Buy-in:", self.buy_in_input)
        form.addRow("Opponents:", self.opponents_input)
        form.addRow("Small blind:", self.small_blind_input)
        form.addRow("Big blind:", self.big_blind_input)
        form.addRow("Difficulty:", self.difficulty_input)

        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(self.start_button)

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(title)
        layout.addLayout(form)
        layout.addWidget(self.error_label)
        layout.addLayout(button_row)
        layout.addStretch()

    def get_settings(self) -> LobbySettings:
        """Build a LobbySettings from the current field values (unvalidated)."""
        return LobbySettings(
            player_name=self.name_input.text().strip(),
            buy_in=self.buy_in_input.value(),
            num_opponents=self.opponents_input.value(),
            difficulty=self.difficulty_input.currentData(),
            small_blind=self.small_blind_input.value(),
            big_blind=self.big_blind_input.value(),
        )

    def validate(self, settings: LobbySettings) -> str:
        """Check the settings for problems the spinboxes' ranges can't catch.

        Returns:
            An error message if invalid, or an empty string if valid.
        """
        if not settings.player_name:
            return "Please enter your name."
        if settings.big_blind < settings.small_blind:
            return "Big blind must be at least the small blind."
        if settings.buy_in < settings.big_blind:
            return "Buy-in must be at least the big blind."
        return ""

    def _on_start_clicked(self) -> None:
        settings = self.get_settings()
        error = self.validate(settings)
        if error:
            self.error_label.setText(error)
            self.error_label.setVisible(True)
            return

        self.error_label.setVisible(False)
        self.start_requested.emit(settings)
