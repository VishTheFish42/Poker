"""Demo: plays several hands of Texas Hold'em through GameController with
simple randomized decisions for every seat, printing the full game log.

This is not part of the engine or its test suite - it's a standalone,
rerunnable way to *watch* the engine actually play poker (dealing, betting,
folds, side pots, showdowns) rather than just trusting test pass counts.

Run with: python scripts/demo_multihand.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from poker.engine.table import Table
from poker.engine.controller import GameController
from poker.engine.player import Player

NUM_PLAYERS = 4
STARTING_STACK = 1000
SMALL_BLIND = 5
BIG_BLIND = 10
NUM_HANDS = 8


def choose_action(gc: GameController) -> None:
    """Pick a random legal action, weighted toward calling/checking so hands
    actually reach showdown sometimes, with occasional bets/raises/folds.
    """
    legal = gc.get_legal_actions()
    options, weights = [], []

    if legal["can_check"]:
        options.append("check")
        weights.append(5)
    if legal["can_call"]:
        options.append("call")
        weights.append(5)
    if legal["can_bet"]:
        options.append("bet")
        weights.append(1)
    if legal["can_raise"]:
        options.append("raise")
        weights.append(1)
    if not legal["can_check"]:
        options.append("fold")
        weights.append(2)

    choice = random.choices(options, weights=weights, k=1)[0]

    if choice in ("check", "call"):
        gc.check_or_call()
    elif choice == "fold":
        gc.fold()
    elif choice == "bet":
        amount = min(legal["min_bet"] * random.choice([1, 2]), legal["max_bet"])
        gc.bet(amount)
    elif choice == "raise":
        amount = min(legal["min_raise"] * random.choice([1, 2]), legal["max_raise"])
        gc.raise_by(amount)


def main() -> None:
    random.seed(42)  # reproducible output for inspection

    table = Table(NUM_PLAYERS)
    players = [Player(f"Player{i}", i, STARTING_STACK) for i in range(NUM_PLAYERS)]
    for p in players:
        table.add_player(p)

    gc = GameController(table, SMALL_BLIND, BIG_BLIND)

    for _ in range(NUM_HANDS):
        active = [p for p in players if p.stack > 0]
        if len(active) < 2:
            print(f"Only {len(active)} player(s) left with chips - stopping early.")
            break

        log_start = len(gc.log)
        gc.start_new_hand()

        while not gc.is_hand_complete:
            choose_action(gc)

        for line in gc.log[log_start:]:
            print(line)
        print()

    print("=== Final stacks ===")
    for p in players:
        print(f"{p.name}: ${p.stack}")
    total = sum(p.stack for p in players)
    expected = NUM_PLAYERS * STARTING_STACK
    print(f"Total chips in play: ${total} (expected ${expected}) -> {'OK' if total == expected else 'MISMATCH!'}")


if __name__ == "__main__":
    main()
