"""Unit tests for showdown resolution and tie-breaking."""

import pytest
from src.poker.engine.showdown import Showdown, ShowdownResult, PlayerResult
from src.poker.engine.player import Player
from src.poker.engine.card import Card, CardSuit, CardRank
from src.poker.engine.pot_manager import PotManager

R = CardRank
S = CardSuit


def card(rank: CardRank, suit: CardSuit) -> Card:
    return Card(suit, rank)


def make_player(seat: int, name: str, hole: list, stack: int = 1000) -> Player:
    p = Player(name, seat, stack)
    p.hole_cards = hole
    return p


def make_pm(contributions: dict) -> PotManager:
    pm = PotManager()
    pm.calculate_pots(contributions)
    return pm


# Standard community board used across most tests:
# 2♣ 7♥ Q♦ K♠ A♥
BOARD = [
    card(R.TWO, S.CLUBS),
    card(R.SEVEN, S.HEARTS),
    card(R.QUEEN, S.DIAMONDS),
    card(R.KING, S.SPADES),
    card(R.ACE, S.HEARTS),
]


class TestPlayerResult:
    def test_fields(self):
        pr = PlayerResult(0, "Alice", [], None, 500)
        assert pr.seat == 0
        assert pr.name == "Alice"
        assert pr.chips_won == 500
        assert pr.best_hand is None

    def test_repr_folded(self):
        pr = PlayerResult(1, "Bob", [], None, 0)
        assert "Bob" in repr(pr) and "folded" in repr(pr)

    def test_repr_with_hand(self):
        from src.poker.engine.hand_evaluator import Hand, HandType
        hand = Hand(HandType.ONE_PAIR, 5, [], [])
        pr = PlayerResult(0, "Alice", [], hand, 200)
        assert "Alice" in repr(pr) and "ONE_PAIR" in repr(pr)


class TestShowdownResult:
    def test_winners_non_zero_chips(self):
        results = [
            PlayerResult(0, "Alice", [], None, 300),
            PlayerResult(1, "Bob",   [], None, 0),
        ]
        sr = ShowdownResult(results, is_showdown=True)
        assert len(sr.winners) == 1
        assert sr.winners[0].seat == 0

    def test_total_pot(self):
        results = [
            PlayerResult(0, "Alice", [], None, 200),
            PlayerResult(1, "Bob",   [], None, 100),
        ]
        sr = ShowdownResult(results, is_showdown=True)
        assert sr.total_pot == 300

    def test_is_showdown_flag(self):
        assert ShowdownResult([], is_showdown=True).is_showdown
        assert not ShowdownResult([], is_showdown=False).is_showdown

    def test_repr(self):
        results = [PlayerResult(0, "Alice", [], None, 100)]
        sr = ShowdownResult(results, is_showdown=False)
        assert "ShowdownResult" in repr(sr)


class TestFoldWin:
    """Single remaining player wins without a showdown."""

    def test_sole_player_wins_entire_pot(self):
        player = make_player(0, "Alice", [card(R.TWO, S.HEARTS), card(R.THREE, S.SPADES)])
        pm = make_pm({0: 300})

        result = Showdown.resolve([player], [], pm)

        assert not result.is_showdown
        assert result.player_results[0].chips_won == 300
        assert len(result.winners) == 1

    def test_sole_player_stack_credited(self):
        player = make_player(0, "Alice", [card(R.TWO, S.HEARTS), card(R.THREE, S.SPADES)], stack=700)
        pm = make_pm({0: 300})

        Showdown.resolve([player], [], pm)

        assert player.stack == 1000  # 700 + 300

    def test_no_community_cards_required_for_fold_win(self):
        player = make_player(0, "Alice", [card(R.TWO, S.HEARTS), card(R.THREE, S.SPADES)])
        pm = make_pm({0: 100, 1: 100})  # second player contributed but folded

        # Folded player is absent from active_players; sole player wins all pots
        result = Showdown.resolve([player], [], pm)
        assert result.player_results[0].chips_won == 200

    def test_fold_win_hand_is_none(self):
        """Winning without showdown does not evaluate or expose hole cards."""
        player = make_player(0, "Alice", [card(R.TWO, S.HEARTS), card(R.THREE, S.SPADES)])
        result = Showdown.resolve([player], [], make_pm({0: 50}))
        assert result.player_results[0].best_hand is None


class TestShowdownClearWinner:
    """Multi-player showdowns where one hand is clearly stronger."""

    def test_trips_beat_one_pair(self):
        # Board: 2♣ 7♥ Q♦ K♠ A♥
        # Alice: A♠ A♦ → trips aces (A-A-A-K-Q)
        # Bob:   2♥ 3♦ → one pair twos (2-2-A-K-Q)
        alice = make_player(0, "Alice", [card(R.ACE, S.SPADES), card(R.ACE, S.DIAMONDS)])
        bob   = make_player(1, "Bob",   [card(R.TWO, S.HEARTS), card(R.THREE, S.DIAMONDS)])
        pm = make_pm({0: 100, 1: 100})

        result = Showdown.resolve([alice, bob], BOARD, pm)

        assert result.is_showdown
        assert result.player_results[0].chips_won == 200
        assert result.player_results[1].chips_won == 0

    def test_winner_stack_is_credited(self):
        alice = make_player(0, "Alice", [card(R.ACE, S.SPADES), card(R.ACE, S.DIAMONDS)], stack=900)
        bob   = make_player(1, "Bob",   [card(R.TWO, S.HEARTS), card(R.THREE, S.DIAMONDS)], stack=900)
        pm = make_pm({0: 100, 1: 100})

        Showdown.resolve([alice, bob], BOARD, pm)

        assert alice.stack == 1100  # 900 + 200
        assert bob.stack == 900     # unchanged

    def test_best_hand_evaluated_for_each_player(self):
        alice = make_player(0, "Alice", [card(R.ACE, S.SPADES), card(R.ACE, S.DIAMONDS)])
        bob   = make_player(1, "Bob",   [card(R.TWO, S.HEARTS), card(R.THREE, S.DIAMONDS)])
        pm = make_pm({0: 100, 1: 100})

        result = Showdown.resolve([alice, bob], BOARD, pm)

        assert result.player_results[0].best_hand is not None
        assert result.player_results[1].best_hand is not None

    def test_three_way_showdown_trips_ranking(self):
        # Board: 2♣ 7♥ Q♦ K♠ A♥
        # Alice: A♠ A♦ → trip aces  (rank 14)
        # Bob:   K♥ K♦ → trip kings (rank 13)
        # Carol: 2♥ 2♦ → trip twos  (rank  2)
        alice = make_player(0, "Alice", [card(R.ACE,  S.SPADES),   card(R.ACE,   S.DIAMONDS)])
        bob   = make_player(1, "Bob",   [card(R.KING, S.HEARTS),   card(R.KING,  S.DIAMONDS)])
        carol = make_player(2, "Carol", [card(R.TWO,  S.HEARTS),   card(R.TWO,   S.DIAMONDS)])
        pm = make_pm({0: 100, 1: 100, 2: 100})

        result = Showdown.resolve([alice, bob, carol], BOARD, pm)

        assert result.player_results[0].chips_won == 300
        assert result.player_results[1].chips_won == 0
        assert result.player_results[2].chips_won == 0

    def test_hole_cards_preserved_in_result(self):
        hole = [card(R.ACE, S.SPADES), card(R.ACE, S.DIAMONDS)]
        alice = make_player(0, "Alice", hole)
        bob   = make_player(1, "Bob",   [card(R.TWO, S.HEARTS), card(R.THREE, S.DIAMONDS)])
        pm = make_pm({0: 100, 1: 100})

        result = Showdown.resolve([alice, bob], BOARD, pm)

        assert result.player_results[0].hole_cards == hole


class TestTieBreaking:
    """Hands that tie split the pot with proper remainder handling."""

    def test_identical_straights_split_pot(self):
        # Board: 2♣ 7♥ Q♦ K♠ A♥
        # Both players hold J-10 → make the same A-K-Q-J-10 straight
        alice = make_player(0, "Alice", [card(R.JACK, S.CLUBS),  card(R.TEN, S.CLUBS)])
        bob   = make_player(1, "Bob",   [card(R.JACK, S.HEARTS), card(R.TEN, S.HEARTS)])
        pm = make_pm({0: 100, 1: 100})

        result = Showdown.resolve([alice, bob], BOARD, pm)

        assert result.player_results[0].chips_won == 100
        assert result.player_results[1].chips_won == 100

    def test_kicker_breaks_pair_tie(self):
        # Board: 2♣ 7♥ Q♦ K♠ A♥
        # Alice: A♠ Q♠ → two pair (A-A-Q-Q-K) ... wait, there's only one Q on board.
        # Let me use: Alice: A♠ 7♠ → two pair (A-A-7-7-K), Bob: A♣ 7♣ → same two pair
        # Tie — both have A-A-7-7-K. Split pot.
        alice = make_player(0, "Alice", [card(R.ACE, S.SPADES),  card(R.SEVEN, S.SPADES)])
        bob   = make_player(1, "Bob",   [card(R.ACE, S.CLUBS),   card(R.SEVEN, S.CLUBS)])
        pm = make_pm({0: 150, 1: 150})

        result = Showdown.resolve([alice, bob], BOARD, pm)

        assert result.player_results[0].chips_won == 150
        assert result.player_results[1].chips_won == 150

    def test_kicker_resolves_one_pair_tie(self):
        # Board: 2♣ 7♥ Q♦ K♠ A♥
        # Alice: 2♠ K♣ → two pair (K-K-2-2-A)
        # Bob:   2♥ Q♣ → two pair (Q-Q-2-2-A)
        # Alice wins (pair of kings beats pair of queens)
        alice = make_player(0, "Alice", [card(R.TWO, S.SPADES), card(R.KING, S.CLUBS)])
        bob   = make_player(1, "Bob",   [card(R.TWO, S.HEARTS), card(R.QUEEN, S.CLUBS)])
        pm = make_pm({0: 200, 1: 200})

        result = Showdown.resolve([alice, bob], BOARD, pm)

        assert result.player_results[0].chips_won == 400
        assert result.player_results[1].chips_won == 0

    def test_three_way_tie_odd_chip(self):
        # Force a 100-chip pot shared by 3 tied players (100 / 3 = 33 r1)
        # Board: all three share the best hand via board cards
        # Use board: A♠ K♠ Q♠ J♠ 10♠ → royal flush on board, everyone ties
        royal_board = [
            card(R.ACE,   S.SPADES),
            card(R.KING,  S.SPADES),
            card(R.QUEEN, S.SPADES),
            card(R.JACK,  S.SPADES),
            card(R.TEN,   S.SPADES),
        ]
        # Give each player irrelevant hole cards (off-suit low cards)
        p0 = make_player(0, "Alice", [card(R.TWO,  S.HEARTS), card(R.THREE, S.HEARTS)])
        p1 = make_player(1, "Bob",   [card(R.FOUR, S.HEARTS), card(R.FIVE,  S.HEARTS)])
        p2 = make_player(2, "Carol", [card(R.SIX,  S.HEARTS), card(R.EIGHT, S.HEARTS)])

        pm = PotManager()
        pm.pots = []  # Manually set a 100-chip pot so remainder is 1
        from src.poker.engine.pot_manager import Pot
        pm.pots = [Pot(100, [0, 1, 2])]

        result = Showdown.resolve([p0, p1, p2], royal_board, pm)

        total = sum(r.chips_won for r in result.player_results)
        assert total == 100
        # Seat 0 (Alice) is lowest seat, gets the odd chip
        chips = {r.seat: r.chips_won for r in result.player_results}
        assert chips[0] == 34
        assert chips[1] == 33
        assert chips[2] == 33


class TestSidePots:
    """All-in players compete only for the pots they contributed to."""

    def test_all_in_player_wins_main_pot_only(self):
        # Board: 2♣ 7♥ Q♦ K♠ A♥
        # Alice (all-in 200): A♠ A♦ → trip aces — best hand
        # Bob   (400):        2♥ 3♦ → one pair twos
        # Carol (400):        4♣ 5♠ → high card ace
        # Pots: main 600 (all), side 400 (Bob + Carol)
        alice = make_player(0, "Alice", [card(R.ACE, S.SPADES),  card(R.ACE,   S.DIAMONDS)])
        bob   = make_player(1, "Bob",   [card(R.TWO, S.HEARTS),  card(R.THREE, S.DIAMONDS)])
        carol = make_player(2, "Carol", [card(R.FOUR, S.CLUBS),  card(R.FIVE,  S.SPADES)])
        pm = make_pm({0: 200, 1: 400, 2: 400})

        result = Showdown.resolve([alice, bob, carol], BOARD, pm)

        chips = {r.seat: r.chips_won for r in result.player_results}
        assert chips[0] == 600   # main pot
        assert chips[1] == 400   # side pot (pair of 2s beats high card)
        assert chips[2] == 0

    def test_all_in_player_loses_all_pots(self):
        # Board: 2♣ 7♥ Q♦ K♠ A♥
        # Alice (all-in 200): 4♣ 5♠ → high card ace
        # Bob   (400):        A♠ A♦ → trip aces — best hand overall
        # Main pot (600): Bob wins; side pot (400): Bob wins
        alice = make_player(0, "Alice", [card(R.FOUR, S.CLUBS), card(R.FIVE,  S.SPADES)])
        bob   = make_player(1, "Bob",   [card(R.ACE,  S.SPADES), card(R.ACE,  S.DIAMONDS)])
        pm = make_pm({0: 200, 1: 400})

        result = Showdown.resolve([alice, bob], BOARD, pm)

        chips = {r.seat: r.chips_won for r in result.player_results}
        assert chips[0] == 0
        assert chips[1] == 600   # wins both pots

    def test_uncalled_bet_returned_to_bettor(self):
        # Alice bet 1000, Bob only had 500 and went all-in, Bob has best hand
        # Main pot 1000 → Bob wins; excess 500 → Alice gets back
        alice = make_player(0, "Alice", [card(R.FOUR, S.CLUBS), card(R.FIVE,  S.SPADES)])
        bob   = make_player(1, "Bob",   [card(R.ACE,  S.SPADES), card(R.ACE,  S.DIAMONDS)])
        pm = make_pm({0: 1000, 1: 500})

        result = Showdown.resolve([alice, bob], BOARD, pm)

        chips = {r.seat: r.chips_won for r in result.player_results}
        assert chips[1] == 1000  # wins the contested pot
        assert chips[0] == 500   # uncalled 500 returned

    def test_side_pot_tie_between_eligible_players(self):
        # Board: 2♣ 7♥ Q♦ K♠ A♥
        # Alice (all-in 200): 4♣ 5♠ → high card A (weakest)
        # Bob   (400): J♣ 10♣ → straight A-K-Q-J-10
        # Carol (400): J♥ 10♥ → straight A-K-Q-J-10 (ties Bob)
        # Main pot 600: Bob and Carol tie (Alice eliminated) → 300 each
        # Side pot 400: Bob and Carol tie → 200 each
        alice = make_player(0, "Alice", [card(R.FOUR, S.CLUBS),  card(R.FIVE,  S.SPADES)])
        bob   = make_player(1, "Bob",   [card(R.JACK, S.CLUBS),  card(R.TEN,   S.CLUBS)])
        carol = make_player(2, "Carol", [card(R.JACK, S.HEARTS), card(R.TEN,   S.HEARTS)])
        pm = make_pm({0: 200, 1: 400, 2: 400})

        result = Showdown.resolve([alice, bob, carol], BOARD, pm)

        chips = {r.seat: r.chips_won for r in result.player_results}
        assert chips[0] == 0
        assert chips[1] == 500   # 300 (main) + 200 (side)
        assert chips[2] == 500   # 300 (main) + 200 (side)


class TestEdgeCases:
    def test_no_active_players(self):
        pm = PotManager()
        result = Showdown.resolve([], [], pm)
        assert result.player_results == []
        assert not result.is_showdown
        assert result.total_pot == 0

    def test_showdown_raises_with_wrong_community_count(self):
        alice = make_player(0, "Alice", [card(R.ACE, S.SPADES), card(R.ACE, S.DIAMONDS)])
        bob   = make_player(1, "Bob",   [card(R.TWO, S.HEARTS), card(R.THREE, S.DIAMONDS)])
        pm = make_pm({0: 100, 1: 100})

        with pytest.raises(ValueError, match="5 community cards"):
            Showdown.resolve([alice, bob], BOARD[:3], pm)

    def test_chips_conserved_across_result(self):
        alice = make_player(0, "Alice", [card(R.ACE,  S.SPADES),   card(R.ACE,   S.DIAMONDS)])
        bob   = make_player(1, "Bob",   [card(R.TWO,  S.HEARTS),   card(R.THREE, S.DIAMONDS)])
        carol = make_player(2, "Carol", [card(R.FOUR, S.CLUBS),    card(R.FIVE,  S.SPADES)])
        pm = make_pm({0: 300, 1: 700, 2: 500})

        result = Showdown.resolve([alice, bob, carol], BOARD, pm)

        assert result.total_pot == pm.get_total()

    def test_two_player_all_in_winner_takes_all(self):
        alice = make_player(0, "Alice", [card(R.ACE, S.SPADES), card(R.ACE, S.DIAMONDS)], stack=0)
        bob   = make_player(1, "Bob",   [card(R.TWO, S.HEARTS), card(R.THREE, S.DIAMONDS)], stack=0)
        pm = make_pm({0: 500, 1: 500})

        result = Showdown.resolve([alice, bob], BOARD, pm)

        assert alice.stack == 1000
        assert bob.stack == 0


if __name__ == "__main__":
    import pytest as _pytest
    _pytest.main([__file__, "-v"])
