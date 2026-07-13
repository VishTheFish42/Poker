"""Shared pytest fixtures."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """A single QApplication instance shared across all Qt widget tests.

    Qt only allows one QApplication per process, so this is session-scoped
    rather than created fresh per test.
    """
    app = QApplication.instance() or QApplication([])
    yield app
