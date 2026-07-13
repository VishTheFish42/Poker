"""Result dialog: shows hand resolution and round summary at showdown.

Displays a real engine `ShowdownResult` (see poker.engine.showdown) - each
player's revealed hand and hand ranking at a real showdown, or just the
winner for an uncontested (fold-win) pot.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

from ..engine.showdown import PlayerResult, ShowdownResult


def _format_player_row(result: PlayerResult, is_showdown: bool) -> QLabel:
    """Build a single player's result line."""
    is_winner = result.chips_won > 0

    if is_showdown and result.best_hand is not None:
        hole = " ".join(repr(card) for card in result.hole_cards)
        hand_desc = result.best_hand.hand_type.name.replace("_", " ").title()
        text = f"{result.name}: {hole} ({hand_desc})"
    else:
        text = result.name

    if is_winner:
        text += f" - wins ${result.chips_won}"

    label = QLabel(text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if is_winner:
        label.setStyleSheet("font-weight: bold; color: #27ae60;")
    return label


class ResultDialog(QDialog):
    """Modal dialog summarizing a completed hand's showdown/fold-win result."""

    def __init__(self, result: ShowdownResult, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.result = result
        self.setWindowTitle("Showdown" if result.is_showdown else "Hand Complete")

        layout = QVBoxLayout(self)

        title = QLabel("Showdown" if result.is_showdown else "Hand Complete")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        if not result.is_showdown and result.player_results:
            winner = result.player_results[0]
            summary = QLabel(f"{winner.name} wins the pot uncontested (${winner.chips_won})")
            summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(summary)
        else:
            for player_result in result.player_results:
                layout.addWidget(_format_player_row(player_result, result.is_showdown))

        pot_label = QLabel(f"Total pot: ${result.total_pot}")
        pot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(pot_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Continue")
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
