"""Small reusable Qt animation helpers for UI polish (Task 4.7)."""

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

DEFAULT_FADE_DURATION_MS = 200


def fade_in(widget: QWidget, duration: int = DEFAULT_FADE_DURATION_MS) -> QPropertyAnimation:
    """Briefly fade `widget` in from transparent to fully opaque.

    Used to draw the eye to something that just changed - a revealed
    card, a seat becoming active, an updated pot, a newly shown screen -
    without altering any of the widget's actual state; it's a purely
    visual overlay layered on top via a graphics effect.

    Returns the animation so callers can keep a reference alive until it
    finishes (Qt does not keep animations alive on their own).
    """
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    animation = QPropertyAnimation(effect, b"opacity", widget)
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.finished.connect(lambda: widget.setGraphicsEffect(None))
    widget._fade_animation = animation  # keep it alive until it finishes
    animation.start()
    return animation
