"""Entry point for the Poker desktop application."""

from poker.ui.main_window import MainWindow


def main() -> None:
    window = MainWindow()
    window.run()


if __name__ == "__main__":
    main()
