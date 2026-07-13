"""Unit tests for the shared fade-in animation helper (Task 4.7)."""

import pytest
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel

from src.poker.ui.effects import fade_in


class TestFadeIn:
    def test_applies_opacity_effect(self, qapp):
        widget = QLabel("hi")
        fade_in(widget)
        assert isinstance(widget.graphicsEffect(), QGraphicsOpacityEffect)

    def test_animation_bounds_and_duration(self, qapp):
        widget = QLabel("hi")
        animation = fade_in(widget, duration=123)
        assert animation.duration() == 123
        assert animation.startValue() == 0.0
        assert animation.endValue() == 1.0

    def test_keeps_a_reference_alive_on_the_widget(self, qapp):
        widget = QLabel("hi")
        animation = fade_in(widget)
        assert widget._fade_animation is animation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
