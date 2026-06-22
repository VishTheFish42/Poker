"""Pot pooling and side pot management for poker."""

from dataclasses import dataclass, field
from typing import Dict, List

from .hand_evaluator import Hand


@dataclass
class Pot:
    """A single pot (main or side) with its eligible contestants."""

    amount: int
    eligible_seats: List[int] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"Pot(${self.amount}, eligible={self.eligible_seats})"


class PotManager:
    """Builds and awards the main pot and any side pots for a hand.

    Side pots arise when a player is all-in for less than the largest bet.
    Each pot tracks which seats contributed to that level and are therefore
    eligible to win it.
    """

    def __init__(self) -> None:
        self.pots: List[Pot] = []

    def __repr__(self) -> str:
        return f"PotManager(total=${self.get_total()}, {len(self.pots)} pot(s))"

    def reset(self) -> None:
        """Clear all pots."""
        self.pots = []

    def get_total(self) -> int:
        """Return total chips across all pots."""
        return sum(pot.amount for pot in self.pots)

    def calculate_pots(self, contributions: Dict[int, int]) -> None:
        """Build main pot and side pots from player contributions.

        Works by repeatedly peeling off the smallest all-in level: every
        player contributes up to that level into one pot, then the process
        repeats on any leftover amounts. A player who contributed less than
        the maximum is only eligible for pots at or below their level.

        Args:
            contributions: {seat: total chips contributed this hand}
        """
        self.pots = []
        if not contributions:
            return

        remaining = dict(contributions)

        while remaining:
            cap = min(remaining.values())
            pot_amount = cap * len(remaining)
            self.pots.append(Pot(pot_amount, list(remaining.keys())))
            remaining = {
                seat: amount - cap
                for seat, amount in remaining.items()
                if amount - cap > 0
            }

    def award_pots(self, hands: Dict[int, Hand]) -> Dict[int, int]:
        """Determine chip winnings for each pot and return them.

        For each pot the eligible player(s) with the strongest hand win.
        Ties split evenly; indivisible remainder chips go one-per-winner
        in ascending seat-number order.

        Players who folded (absent from `hands`) cannot win any pot even
        if listed in that pot's eligible_seats.

        Args:
            hands: {seat: best Hand} for players still in the hand (not folded)

        Returns:
            {seat: chips won} for every seat present in `hands`
        """
        winnings: Dict[int, int] = {seat: 0 for seat in hands}

        for pot in self.pots:
            contenders = [s for s in pot.eligible_seats if s in hands]

            if not contenders:
                continue

            if len(contenders) == 1:
                winnings[contenders[0]] += pot.amount
                continue

            best = max(hands[s] for s in contenders)
            winners = sorted(s for s in contenders if hands[s] == best)

            share, remainder = divmod(pot.amount, len(winners))
            for seat in winners:
                winnings[seat] += share
            for i in range(remainder):
                winnings[winners[i]] += 1

        return winnings
