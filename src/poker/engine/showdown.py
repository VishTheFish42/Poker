"""Showdown resolution and tie-breaking for Texas Hold'em."""

from typing import Dict, List, Optional

from .card import Card
from .hand_evaluator import Hand, HandEvaluator
from .player import Player
from .pot_manager import PotManager


class PlayerResult:
    """Outcome for a single player at the end of a hand."""

    def __init__(
        self,
        seat: int,
        name: str,
        hole_cards: List[Card],
        best_hand: Optional[Hand],
        chips_won: int = 0,
    ) -> None:
        self.seat = seat
        self.name = name
        self.hole_cards = hole_cards
        self.best_hand = best_hand
        self.chips_won = chips_won

    def __repr__(self) -> str:
        hand_str = repr(self.best_hand) if self.best_hand else "folded"
        return f"PlayerResult({self.name}, seat={self.seat}, {hand_str}, won=${self.chips_won})"


class ShowdownResult:
    """The complete outcome of a hand."""

    def __init__(self, player_results: List[PlayerResult], is_showdown: bool) -> None:
        self.player_results = player_results
        # True when 2+ players compare cards; False when a single player wins by fold
        self.is_showdown = is_showdown

    def __repr__(self) -> str:
        names = [r.name for r in self.winners]
        return f"ShowdownResult(is_showdown={self.is_showdown}, winners={names})"

    @property
    def winners(self) -> List[PlayerResult]:
        """Players who won chips in this hand."""
        return [r for r in self.player_results if r.chips_won > 0]

    @property
    def total_pot(self) -> int:
        """Total chips distributed."""
        return sum(r.chips_won for r in self.player_results)


class Showdown:
    """Resolves the showdown at the end of a poker hand.

    Evaluates each active player's best hand from their hole cards and the
    community board, awards pots to the strongest eligible hand(s) with
    tie-breaking, and credits chips to player stacks.
    """

    @staticmethod
    def resolve(
        active_players: List[Player],
        community_cards: List[Card],
        pot_manager: PotManager,
    ) -> ShowdownResult:
        """Evaluate hands, award pots, and credit chips to player stacks.

        Args:
            active_players: Players still in the hand (not folded). Each must
                have exactly 2 hole cards when 2+ players remain.
            community_cards: The 5 board cards. Required only when 2+ players
                remain (a fold-win ends before the board is complete).
            pot_manager: PotManager with pots already calculated for this hand.

        Returns:
            ShowdownResult with per-player outcomes. Each winning player's
            stack is increased by their winnings as a side effect.

        Raises:
            ValueError: If 2+ active players remain but fewer than 5 community
                cards are provided.
        """
        if not active_players:
            return ShowdownResult(player_results=[], is_showdown=False)

        is_showdown = len(active_players) > 1
        hands: Dict[int, Hand] = {}
        winnings: Dict[int, int]

        if is_showdown:
            if len(community_cards) != 5:
                raise ValueError(
                    f"Showdown requires exactly 5 community cards, got {len(community_cards)}"
                )
            for player in active_players:
                seven = list(player.hole_cards) + list(community_cards)
                hands[player.seat] = HandEvaluator.best_hand_from_seven(seven)
            winnings = pot_manager.award_pots(hands)
        else:
            sole = active_players[0]
            winnings = {sole.seat: pot_manager.get_total()}

        # Credit chips to stacks
        for player in active_players:
            won = winnings.get(player.seat, 0)
            if won > 0:
                player.add_chips(won)

        player_results = [
            PlayerResult(
                seat=p.seat,
                name=p.name,
                hole_cards=list(p.hole_cards),
                best_hand=hands.get(p.seat),
                chips_won=winnings.get(p.seat, 0),
            )
            for p in active_players
        ]

        return ShowdownResult(player_results=player_results, is_showdown=is_showdown)
