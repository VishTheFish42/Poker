"""Entry point for the Poker desktop application."""

import sys
from pathlib import Path

# The `poker` package lives under src/ and isn't pip-installed, so put it on
# the path before importing it.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from poker.ui.main_window import MainWindow  # noqa: E402


def main() -> int:
    """Launch the Poker desktop application.

    Returns:
        The process exit code from the Qt event loop.
    """
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
