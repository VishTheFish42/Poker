"""Table screen: seat layout, chip stacks, community cards, and player names.

Renders a real engine `Table` (see poker.engine.table) directly - seats
arranged radially using each `Seat.position_angle`, per-seat name/stack/
current-bet/status, dealer button and blind markers, and the community
cards / pot. `ActionPanel` (4.4) provides fold/check-call/bet-raise/all-in
controls driven by a `GameController.get_legal_actions()` dict, and
`GameLogView` (4.5) shows `GameController.log` plus the current turn's
status line from `GameController.get_action_prompt()`. Each of these takes
the engine's own data shapes directly, so Task 6.1 just has to wire
signals and feed updates in - no view-model translation needed. The
`restart_requested` signal (4.6) is wired to lobby navigation in
`MainWindow`; actually tearing down/recreating a `GameController` on
restart is Task 6.3's job.

Card faces are drawn (not photographed), and reveals/highlight changes/pot
updates fade in via `poker.ui.effects.fade_in` (Task 4.7) - see that
module for why animations are implemented as transient graphics-effect
overlays rather than mutating persistent widget state.
"""

import math
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..engine.card import Card, CardSuit
from ..engine.player import PlayerStatus, Seat
from ..engine.table import Table
from .effects import fade_in

COMMUNITY_CARD_SLOTS = 5
RED_SUITS = (CardSuit.HEARTS, CardSuit.DIAMONDS)

EMPTY_SEAT_STYLE = "SeatWidget { background: #1b1b1b; border: 2px dashed #555; border-radius: 10px; }"
BASE_SEAT_STYLE = (
    "SeatWidget { background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    " stop:0 #34495e, stop:1 #212f3c); border: 2px solid #5d6d7e; border-radius: 10px; }"
)
ACTIVE_SEAT_STYLE = (
    "SeatWidget { background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
    " stop:0 #34495e, stop:1 #212f3c); border: 3px solid #2ecc71; border-radius: 10px; }"
)
SEATS_FELT_STYLE = (
    "SeatsArea { background: qradialgradient(cx:0.5, cy:0.45, radius:0.9, fx:0.5, fy:0.45,"
    " stop:0 #1e7a45, stop:0.85 #145229, stop:1 #0d3b1f);"
    " border: 8px solid #6b4a2b; border-radius: 26px; }"
)
BOARD_AREA_STYLE = "QFrame { background: #0d3b1f; border: 2px solid #6b4a2b; border-radius: 10px; }"
LOG_AREA_STYLE = "GameLogView { background: #1c1c1c; border: 1px solid #444; border-radius: 8px; }"
BUTTON_BASE_STYLE = (
    "QPushButton {{ background: {bg}; color: white; font-weight: bold;"
    " border-radius: 6px; padding: 6px 10px; }}"
    " QPushButton:disabled {{ background: #7f8c8d; color: #d5d5d5; }}"
    " QPushButton:hover:!disabled {{ background: {hover}; }}"
)


class CardLabel(QLabel):
    """A single playing card slot: empty, face-down, or face-up.

    Drawn rather than photographed: a suit-colored watermark (face-up) or
    diagonal weave (face-down) is painted behind the label's own rank/suit
    text in `paintEvent`. A face-up card that's newly revealed (as opposed
    to a redraw of one already showing) fades in via `poker.ui.effects.fade_in`.
    """

    WIDTH = 40
    HEIGHT = 56

    def __init__(self) -> None:
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.state = "empty"
        self._card: Optional[Card] = None
        self.clear_card()

    def set_card(self, card: Card) -> None:
        """Show this card's rank and suit face-up."""
        is_new_reveal = self.state != "face" or self._card != card
        self.state = "face"
        self._card = card
        color = "#c0392b" if card.suit in RED_SUITS else "#1a1a1a"
        self.setText(repr(card))
        self.setStyleSheet(
            f"background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #ecf0f1);"
            f" color: {color}; font-weight: bold; font-size: 13px;"
            " border: 1px solid #333; border-radius: 6px;"
        )
        self.update()
        if is_new_reveal:
            fade_in(self)

    def set_face_down(self) -> None:
        """Show a hidden card back (hole card belonging to another player)."""
        self.state = "back"
        self._card = None
        self.setText("")
        self.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #34495e, stop:1 #22303f);"
            " border: 1px solid #1a2530; border-radius: 6px;"
        )
        self.update()

    def clear_card(self) -> None:
        """Show an empty slot (no card dealt here yet)."""
        self.state = "empty"
        self._card = None
        self.setText("")
        self.setStyleSheet("background: transparent; border: 1px dashed #999; border-radius: 6px;")
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if self.state == "face" and self._card is not None:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            watermark = QColor(192, 57, 43, 45) if self._card.suit in RED_SUITS else QColor(26, 26, 26, 40)
            font = painter.font()
            font.setPointSize(22)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(watermark)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, str(self._card.suit))
            painter.end()
        elif self.state == "back":
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(QColor(255, 255, 255, 28))
            step = 7
            for offset in range(-self.height(), self.width(), step):
                painter.drawLine(offset, self.height(), offset + self.height(), 0)
            painter.end()
        super().paintEvent(event)


class SeatWidget(QFrame):
    """Displays one seat: player name, stack, current bet, cards, and status."""

    WIDTH = 160
    HEIGHT = 150

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.seat_number: Optional[int] = None

        self.marker_label = QLabel()
        self.marker_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.marker_label.setStyleSheet("color: #5dade2; font-weight: bold;")

        self.name_label = QLabel()
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.card_labels = [CardLabel(), CardLabel()]
        cards_row = QHBoxLayout()
        cards_row.addStretch()
        for card_label in self.card_labels:
            cards_row.addWidget(card_label)
        cards_row.addStretch()

        self.stack_label = QLabel()
        self.stack_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stack_label.setStyleSheet("color: #f4f6f6; font-weight: bold;")

        self.bet_label = QLabel()
        self.bet_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bet_label.setStyleSheet("color: #f39c12;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)
        layout.addWidget(self.marker_label)
        layout.addWidget(self.name_label)
        layout.addLayout(cards_row)
        layout.addWidget(self.stack_label)
        layout.addWidget(self.bet_label)

        self._was_active = False
        self.set_empty()

    def set_empty(self) -> None:
        """Show this seat as unoccupied."""
        self.seat_number = None
        self.marker_label.setText("")
        self.name_label.setText("Empty Seat")
        self.name_label.setStyleSheet("color: gray;")
        self.stack_label.setText("")
        self.bet_label.setText("")
        for card_label in self.card_labels:
            card_label.clear_card()
        self._was_active = False
        self.setStyleSheet(EMPTY_SEAT_STYLE)

    def update_from_seat(self, seat: Seat, reveal_cards: bool, is_current: bool) -> None:
        """Refresh this widget from a live engine `Seat`.

        Args:
            seat: The seat to render.
            reveal_cards: Whether to show the occupant's hole cards face up
                (true for the human viewer's own seat).
            is_current: Whether this seat is currently on the clock.
        """
        player = seat.player
        self.seat_number = seat.seat_number
        if player is None:
            self.set_empty()
            return

        name = player.name
        if player.status == PlayerStatus.FOLDED:
            name += " (Folded)"
        elif player.status == PlayerStatus.ALL_IN:
            name += " (All-In)"
        elif player.status == PlayerStatus.SITTING_OUT:
            name += " (Sitting Out)"
        self.name_label.setText(name)
        self.name_label.setStyleSheet("color: gray;" if not player.is_active() else "font-weight: bold;")

        self.stack_label.setText(f"${player.stack}")
        self.bet_label.setText(f"Bet: ${player.current_bet}" if player.current_bet > 0 else "")

        markers = []
        if seat.is_button:
            markers.append("D")
        if seat.is_small_blind:
            markers.append("SB")
        if seat.is_big_blind:
            markers.append("BB")
        self.marker_label.setText("  ".join(markers))

        folded = player.status == PlayerStatus.FOLDED
        for index, card_label in enumerate(self.card_labels):
            if index >= len(player.hole_cards):
                card_label.clear_card()
            elif folded:
                card_label.clear_card()
            elif reveal_cards:
                card_label.set_card(player.hole_cards[index])
            else:
                card_label.set_face_down()

        self.set_active(is_current)

    def set_active(self, active: bool) -> None:
        """Highlight this seat as the one currently on the clock.

        Fades in only on the transition into "active", not on every
        redraw while a seat stays on the clock across UI refreshes.
        """
        became_active = active and not self._was_active
        self._was_active = active
        self.setStyleSheet(ACTIVE_SEAT_STYLE if active else BASE_SEAT_STYLE)
        if became_active:
            fade_in(self)


class SeatsArea(QFrame):
    """Positions a pool of `SeatWidget`s radially around the table felt."""

    DEFAULT_WIDTH = 760
    DEFAULT_HEIGHT = 420
    MARGIN = 10

    def __init__(self, num_seats: int = 6) -> None:
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(SEATS_FELT_STYLE)
        self.setMinimumSize(420, 320)
        self.seat_widgets: List[SeatWidget] = []
        self._angles: List[float] = []
        self.configure(num_seats)

    @property
    def num_seats(self) -> int:
        return len(self.seat_widgets)

    def configure(self, num_seats: int) -> None:
        """Rebuild the seat widget pool to match `num_seats`."""
        for widget in self.seat_widgets:
            widget.setParent(None)
            widget.deleteLater()
        self.seat_widgets = [SeatWidget() for _ in range(num_seats)]
        for widget in self.seat_widgets:
            widget.setParent(self)
            widget.show()
        self._angles = []
        self._reposition()

    def set_angles(self, angles: List[float]) -> None:
        """Set each seat widget's position on the ellipse, in degrees."""
        self._angles = list(angles)
        self._reposition()

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().resizeEvent(event)
        self._reposition()

    def _reposition(self) -> None:
        if not self._angles or not self.seat_widgets:
            return
        width = self.width() if self.width() > SeatWidget.WIDTH else self.DEFAULT_WIDTH
        height = self.height() if self.height() > SeatWidget.HEIGHT else self.DEFAULT_HEIGHT
        center_x, center_y = width / 2, height / 2
        radius_x = max(center_x - SeatWidget.WIDTH / 2 - self.MARGIN, 10)
        radius_y = max(center_y - SeatWidget.HEIGHT / 2 - self.MARGIN, 10)

        for widget, angle in zip(self.seat_widgets, self._angles):
            # Seat 0 sits at the top; angles increase clockwise around the felt.
            radians = math.radians(angle - 90)
            x = center_x + radius_x * math.cos(radians) - SeatWidget.WIDTH / 2
            y = center_y + radius_y * math.sin(radians) - SeatWidget.HEIGHT / 2
            widget.setGeometry(int(x), int(y), SeatWidget.WIDTH, SeatWidget.HEIGHT)


class ActionPanel(QFrame):
    """Fold / check-call / bet-raise / all-in controls for whoever is on
    the clock.

    Each control maps 1:1 to one of `GameController`'s action convenience
    methods, so Task 6.1 only needs to connect these signals to
    `controller.fold` / `check_or_call` / `bet` / `raise_by` / `go_all_in`
    and feed `update_legal_actions()` with `controller.get_legal_actions()`.
    """

    fold_requested = Signal()
    check_call_requested = Signal()
    bet_requested = Signal(int)
    raise_requested = Signal(int)
    all_in_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._bet_mode = "bet"

        self.fold_button = QPushButton("Fold")
        self.fold_button.clicked.connect(self.fold_requested)
        self.fold_button.setStyleSheet(BUTTON_BASE_STYLE.format(bg="#c0392b", hover="#e74c3c"))

        self.check_call_button = QPushButton("Check")
        self.check_call_button.clicked.connect(self.check_call_requested)
        self.check_call_button.setStyleSheet(BUTTON_BASE_STYLE.format(bg="#2980b9", hover="#3498db"))

        self.amount_input = QSpinBox()
        self.amount_input.setRange(0, 0)

        self.bet_raise_button = QPushButton("Bet")
        self.bet_raise_button.clicked.connect(self._on_bet_raise_clicked)
        self.bet_raise_button.setStyleSheet(BUTTON_BASE_STYLE.format(bg="#27ae60", hover="#2ecc71"))

        self.all_in_button = QPushButton("All-In")
        self.all_in_button.clicked.connect(self.all_in_requested)
        self.all_in_button.setStyleSheet(BUTTON_BASE_STYLE.format(bg="#8e44ad", hover="#9b59b6"))

        self._build_layout()
        self.disable_all()

    def _build_layout(self) -> None:
        amount_row = QHBoxLayout()
        amount_row.addWidget(QLabel("Amount:"))
        amount_row.addWidget(self.amount_input)

        buttons_row = QHBoxLayout()
        buttons_row.addWidget(self.fold_button)
        buttons_row.addWidget(self.check_call_button)
        buttons_row.addWidget(self.bet_raise_button)
        buttons_row.addWidget(self.all_in_button)

        layout = QVBoxLayout(self)
        layout.addLayout(amount_row)
        layout.addLayout(buttons_row)

    def disable_all(self) -> None:
        """Disable every control, e.g. while it isn't this seat's turn."""
        for button in (self.fold_button, self.check_call_button, self.bet_raise_button, self.all_in_button):
            button.setEnabled(False)
        self.amount_input.setEnabled(False)
        self.amount_input.setRange(0, 0)
        self.check_call_button.setText("Check")
        self.bet_raise_button.setText("Bet")

    def update_legal_actions(self, legal: Dict[str, object]) -> None:
        """Enable, disable, and label controls from a
        `GameController.get_legal_actions()` dict.
        """
        self.fold_button.setEnabled(bool(legal.get("can_fold", False)))

        can_check = bool(legal.get("can_check", False))
        can_call = bool(legal.get("can_call", False))
        self.check_call_button.setEnabled(can_check or can_call)
        self.check_call_button.setText(
            "Check" if can_check else f"Call ${legal.get('call_amount', 0)}"
        )

        can_bet = bool(legal.get("can_bet", False))
        can_raise = bool(legal.get("can_raise", False))
        if can_bet:
            self._bet_mode = "bet"
            self.bet_raise_button.setText("Bet")
            self.bet_raise_button.setEnabled(True)
            self.amount_input.setEnabled(True)
            self.amount_input.setRange(legal["min_bet"], legal["max_bet"])
            self.amount_input.setValue(legal["min_bet"])
        elif can_raise:
            self._bet_mode = "raise"
            self.bet_raise_button.setText("Raise")
            self.bet_raise_button.setEnabled(True)
            self.amount_input.setEnabled(True)
            self.amount_input.setRange(legal["min_raise"], legal["max_raise"])
            self.amount_input.setValue(legal["min_raise"])
        else:
            self.bet_raise_button.setText("Bet")
            self.bet_raise_button.setEnabled(False)
            self.amount_input.setEnabled(False)
            self.amount_input.setRange(0, 0)

        self.all_in_button.setEnabled(bool(legal.get("can_all_in", False)))

    def _on_bet_raise_clicked(self) -> None:
        amount = self.amount_input.value()
        if self._bet_mode == "raise":
            self.raise_requested.emit(amount)
        else:
            self.bet_requested.emit(amount)


class GameLogView(QFrame):
    """Status line for whoever is on the clock, plus the scrolling history
    of hand events - both driven directly by `GameController`'s own data:
    `set_status()` takes `get_action_prompt()`'s return value, and
    `set_log()` takes the `log` list itself.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(LOG_AREA_STYLE)

        title = QLabel("Game Log")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; color: #ccc;")

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-style: italic; color: #5dade2;")

        self.log_list = QListWidget()
        self.log_list.setWordWrap(True)
        self.log_list.setStyleSheet(
            "QListWidget { background: #141414; color: #ddd; border: none; }"
        )

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(self.status_label)
        layout.addWidget(self.log_list, stretch=1)

    def set_status(self, prompt: Optional[str]) -> None:
        """Show the current turn's status line (or clear it if None)."""
        self.status_label.setText(prompt or "")

    def set_log(self, messages: List[str]) -> None:
        """Replace the displayed log with `messages`, scrolled to the end."""
        self.log_list.clear()
        self.log_list.addItems(messages)
        self.log_list.scrollToBottom()

    def append_message(self, message: str) -> None:
        """Append a single new line to the log without redrawing the rest."""
        self.log_list.addItem(message)
        self.log_list.scrollToBottom()


class TableView(QWidget):
    """Table screen: board/pot, seats, action panel, and game log regions."""

    restart_requested = Signal()

    def __init__(self, num_seats: int = 6) -> None:
        super().__init__()
        self.setStyleSheet("TableView { background: #1a1a1a; }")
        self._last_pot: Optional[int] = None

        self.restart_button = QPushButton("Restart")
        self.restart_button.clicked.connect(self.restart_requested)
        self.restart_button.setStyleSheet(BUTTON_BASE_STYLE.format(bg="#616a6b", hover="#7f8c8d"))

        self.pot_label = QLabel("Pot: $0")
        self.pot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pot_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #f1c40f;")

        self.community_cards = [CardLabel() for _ in range(COMMUNITY_CARD_SLOTS)]
        self.board_area = self._make_board_area()

        self.seats_area = SeatsArea(num_seats)
        self.seats_area.set_angles([seat.position_angle for seat in Table(num_seats).seats])

        self.action_area = ActionPanel()
        self.log_area = GameLogView()

        self._build_layout()

    def _make_board_area(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setStyleSheet(BOARD_AREA_STYLE)
        row = QHBoxLayout(frame)
        row.addStretch()
        for card_label in self.community_cards:
            row.addWidget(card_label)
        row.addStretch()
        return frame

    def _build_layout(self) -> None:
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        top_bar.addWidget(self.restart_button)

        center_column = QVBoxLayout()
        center_column.addLayout(top_bar)
        center_column.addWidget(self.pot_label)
        center_column.addWidget(self.board_area, stretch=2)
        center_column.addWidget(self.seats_area, stretch=3)
        center_column.addWidget(self.action_area, stretch=1)

        main_row = QHBoxLayout(self)
        main_row.addLayout(center_column, stretch=3)
        main_row.addWidget(self.log_area, stretch=1)

    def update_from_table(self, table: Table, viewer_seat: Optional[int] = None) -> None:
        """Refresh the pot, community cards, and seats from a live `Table`.

        Args:
            table: The engine table to render.
            viewer_seat: Seat number whose hole cards should be shown face
                up (the human player's seat), or None to keep every seat's
                hole cards hidden.
        """
        if table.total_pot != self._last_pot:
            self.pot_label.setText(f"Pot: ${table.total_pot}")
            fade_in(self.pot_label)
            self._last_pot = table.total_pot

        for index, card_label in enumerate(self.community_cards):
            if index < len(table.community_cards):
                card_label.set_card(table.community_cards[index])
            else:
                card_label.clear_card()

        if self.seats_area.num_seats != table.num_seats:
            self.seats_area.configure(table.num_seats)
        self.seats_area.set_angles([seat.position_angle for seat in table.seats])

        for seat, widget in zip(table.seats, self.seats_area.seat_widgets):
            widget.update_from_seat(
                seat,
                reveal_cards=viewer_seat is not None and seat.seat_number == viewer_seat,
                is_current=table.current_player_seat == seat.seat_number,
            )
