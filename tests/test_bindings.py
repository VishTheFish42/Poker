"""Tests for the pybind11 `poker_engine` module (bindings/module.cpp).

These check the Python-facing API - names, types, ownership, exception
mapping - and drive scripted hands end to end. Rules correctness itself is
covered by the C++ GoogleTest suite under engine/tests/.
"""

import random

import pytest

import poker_engine as pe
from poker_engine import ActionType, HandPhase, ProgressionMode, Rank, Street, Suit

_RANKS = {
    "2": Rank.TWO, "3": Rank.THREE, "4": Rank.FOUR, "5": Rank.FIVE, "6": Rank.SIX,
    "7": Rank.SEVEN, "8": Rank.EIGHT, "9": Rank.NINE, "T": Rank.TEN, "J": Rank.JACK,
    "Q": Rank.QUEEN, "K": Rank.KING, "A": Rank.ACE,
}
_SUITS = {"s": Suit.SPADES, "h": Suit.HEARTS, "d": Suit.DIAMONDS, "c": Suit.CLUBS}


def cards(text):
    """Parse "As Kd 2c" into a list of Cards."""
    return [pe.Card(_SUITS[t[1]], _RANKS[t[0]]) for t in text.split()]


def make_table(*stacks):
    names = ["Alice", "Bob", "Carl", "Dana", "Eve", "Finn"]
    table = pe.Table(len(stacks))
    for seat, stack in enumerate(stacks):
        table.add_player(pe.Player(names[seat], seat, stack))
    return table


def act(game, action_type, amount=0):
    game.submit_action(pe.Action(action_type, game.current_seat, amount))


def check_down(game):
    while game.phase == HandPhase.AWAITING_ACTION:
        act(game, ActionType.CHECK)


def total_chips(game):
    stacks = sum(p.stack for p in game.table.get_all_players())
    return stacks if game.is_hand_complete else stacks + game.table.total_pot


@pytest.fixture
def game():
    """3-handed, blinds 5/10, 1000 each: button 0, SB 1, BB 2, UTG 0."""
    return pe.GameController(make_table(1000, 1000, 1000), 5, 10)


# Hole cards for seats 0-2, then burn + flop, burn + turn, burn + river.
AA_WINS = cards("As Ah Kd Kc 2c 7d 5c 9s 8h 4d 6c 3c 7c Jh")


class TestCardsAndDeck:
    def test_card_properties_and_display(self):
        card = pe.Card(Suit.SPADES, Rank.ACE)
        assert card.suit == Suit.SPADES
        assert card.rank == Rank.ACE
        assert card.rank_value == 14
        assert str(card) == "A♠"
        assert repr(card) == "Card(Suit.SPADES, Rank.ACE)"

    def test_card_equality_hashing_and_rank_ordering(self):
        ace_s, ace_h, two_c = cards("As Ah 2c")
        assert ace_s == pe.Card(Suit.SPADES, Rank.ACE)
        assert ace_s != ace_h
        assert len({ace_s, ace_h, pe.Card(Suit.SPADES, Rank.ACE)}) == 2
        assert two_c < ace_s
        assert not ace_s < ace_h  # ordering is by rank only
        assert sorted([ace_s, two_c]) == [two_c, ace_s]

    def test_deck_deals_stacked_cards_in_order(self):
        deck = pe.Deck()
        assert len(deck) == pe.Deck.FULL_DECK_SIZE == 52
        deck.seed(1)
        deck.shuffle()
        top = cards("As 2h Tc")
        deck.put_on_top(top)
        assert deck.peek_card() == top[0]
        assert [deck.deal_card() for _ in range(3)] == top
        assert deck.remaining == 49

    def test_deck_errors_map_to_python_exceptions(self):
        deck = pe.Deck()
        with pytest.raises(ValueError):
            deck.put_on_top(cards("As As"))
        assert len(deck) == 52
        for _ in range(52):
            deck.deal_card()
        assert deck.is_empty
        with pytest.raises(IndexError):
            deck.deal_card()

    def test_same_seed_same_shuffle(self):
        a, b = pe.Deck(), pe.Deck()
        a.seed(42)
        b.seed(42)
        a.shuffle()
        b.shuffle()
        assert [a.deal_card() for _ in range(52)] == [b.deal_card() for _ in range(52)]


class TestHandEvaluator:
    def test_evaluates_and_compares_hands(self):
        royal = pe.HandEvaluator.evaluate_hand(cards("As Ks Qs Js Ts"))
        pair = pe.HandEvaluator.best_hand_from_seven(cards("2c 2d 5h 9s Jc Kd 3h"))
        assert royal.hand_type == pe.HandType.ROYAL_FLUSH
        assert pair.hand_type == pe.HandType.ONE_PAIR
        assert pair.rank_value == 2
        assert len(pair.cards) == 5
        assert royal > pair

    def test_wrong_card_count_raises_value_error(self):
        with pytest.raises(ValueError):
            pe.HandEvaluator.evaluate_hand(cards("As Ks"))


class TestTableAndPlayers:
    def test_seating_and_snapshots(self):
        table = make_table(1000, 500)
        assert table.num_seats == 2
        assert pe.Table.MAX_PLAYERS == 10
        alice = table.get_player(0)
        assert (alice.name, alice.seat, alice.stack) == ("Alice", 0, 1000)
        assert alice.status == pe.PlayerStatus.ACTIVE
        assert alice.can_act and alice.is_active and alice.has_chips
        assert [p.name for p in table.get_all_players()] == ["Alice", "Bob"]

    def test_empty_seats_and_invalid_seating(self):
        table = pe.Table(3)
        assert table.get_player(1) is None
        assert table.remove_player(1) is None
        table.add_player(pe.Player("Alice", 1, 100))
        with pytest.raises(ValueError):
            table.add_player(pe.Player("Bob", 1, 100))
        with pytest.raises(ValueError):
            table.add_player(pe.Player("Bob", 7, 100))
        with pytest.raises(ValueError):
            pe.Table(11)
        assert table.remove_player(1).name == "Alice"
        assert table.get_player(1) is None

    def test_removed_player_snapshot_stays_valid(self):
        table = make_table(1000, 500)
        bob = table.get_player(1)
        table.remove_player(1)
        assert bob.name == "Bob"
        assert bob.stack == 500


class TestGameController:
    def test_before_first_hand(self, game):
        assert game.phase == HandPhase.NOT_STARTED
        assert game.current_seat is None
        assert game.last_result is None
        assert game.betting_round is None
        assert game.step_once() is False
        with pytest.raises(RuntimeError):
            game.legal_actions()
        with pytest.raises(RuntimeError):
            game.submit_action(pe.Action(ActionType.FOLD, 0))

    def test_controller_works_on_its_own_copy_of_the_table(self):
        table = make_table(1000, 1000)
        game = pe.GameController(table, 5, 10)
        game.start_hand()
        assert game.table.total_pot == 15
        assert table.total_pot == 0
        assert table.get_player(0).stack == 1000

    def test_start_hand_exposes_blinds_position_and_betting(self, game):
        game.start_hand()
        table = game.table
        assert game.hand_number == 1
        assert game.phase == HandPhase.AWAITING_ACTION
        assert game.current_seat == 0
        assert (table.button_seat, table.small_blind_seat, table.big_blind_seat) == (0, 1, 2)
        assert table.is_button(0) and table.is_big_blind(2)
        assert (table.small_blind_amount, table.big_blind_amount) == (5, 10)
        assert table.street == Street.PRE_FLOP
        assert pe.street_number(table.street) == 0
        assert table.total_pot == 15
        assert game.contributions == {1: 5, 2: 10}
        assert all(len(p.hole_cards) == 2 for p in table.get_all_players())

        br = game.betting_round
        assert br.highest_bet == 10
        assert br.min_raise_amount == 10
        assert br.player_bet_amounts == {1: 5, 2: 10}
        assert br.get_amount_to_call(0) == 10
        assert not br.can_check(0)

    def test_legal_actions_facing_big_blind(self, game):
        game.start_hand()
        legal = game.legal_actions()
        assert legal.seat == 0
        assert legal.can_fold and legal.can_call and not legal.can_check
        assert legal.call_amount == 10
        assert not legal.can_bet
        assert legal.can_raise and (legal.min_raise, legal.max_raise) == (10, 990)
        assert legal.can_all_in and legal.all_in_amount == 1000

    def test_illegal_and_out_of_turn_actions(self, game):
        game.start_hand()
        assert game.validate_action(pe.Action(ActionType.CALL, 0)) is None
        reason = game.validate_action(pe.Action(ActionType.CALL, 1))
        assert "seat 0" in reason
        with pytest.raises(ValueError, match="seat 0"):
            game.submit_action(pe.Action(ActionType.CALL, 1))
        with pytest.raises(ValueError):
            act(game, ActionType.CHECK)
        with pytest.raises(ValueError):
            act(game, ActionType.RAISE, 5)
        with pytest.raises(ValueError):
            pe.Action(ActionType.CHECK, 0, 10)  # check can't carry an amount
        assert game.current_seat == 0
        assert game.table.total_pot == 15

    def test_start_hand_errors(self, game):
        with pytest.raises(ValueError):
            game.start_hand(cards("As As"))
        game.start_hand()
        with pytest.raises(RuntimeError):
            game.start_hand()
        with pytest.raises(RuntimeError):
            pe.GameController(make_table(100, 0), 5, 10).start_hand()

    def test_scripted_hand_to_showdown(self, game):
        game.start_hand(AA_WINS)
        assert game.table.get_player(0).hole_cards == cards("As Ah")

        act(game, ActionType.CALL)
        act(game, ActionType.CALL)
        act(game, ActionType.CHECK)
        assert game.table.street == Street.FLOP
        assert game.table.community_cards == cards("9s 8h 4d")
        assert game.table.burned_cards == cards("5c")
        assert game.current_seat == 1
        check_down(game)

        assert game.is_hand_complete
        assert game.table.street == Street.HAND_COMPLETE
        assert game.table.community_cards == cards("9s 8h 4d 3c Jh")
        assert game.table.burned_cards == cards("5c 6c 7c")
        result = game.last_result
        assert result.is_showdown
        assert result.total_pot == 30
        assert [w.seat for w in result.winners] == [0]
        winner = result.winners[0]
        assert winner.name == "Alice"
        assert winner.chips_won == 30
        assert winner.best_hand.hand_type == pe.HandType.ONE_PAIR
        assert [p.stack for p in game.table.get_all_players()] == [1020, 990, 990]

    def test_fold_win_has_no_best_hands(self, game):
        game.start_hand()
        act(game, ActionType.FOLD)
        act(game, ActionType.FOLD)
        result = game.last_result
        assert not result.is_showdown
        assert result.winners[0].seat == 2
        assert result.player_results[0].best_hand is None
        assert game.table.community_cards == []

    def test_side_pots(self):
        game = pe.GameController(make_table(100, 1000, 1000), 5, 10)
        game.start_hand(cards("As Ah Kd Kc Qs Qh 4c 2c 5d 9h 6c Js 7c 3d"))
        act(game, ActionType.ALL_IN)
        act(game, ActionType.RAISE, 100)
        act(game, ActionType.CALL)
        check_down(game)

        assert [(p.amount, p.eligible_seats) for p in game.pots] == [(300, [0, 1, 2]), (200, [1, 2])]
        assert [p.stack for p in game.table.get_all_players()] == [300, 1000, 800]
        assert game.contributions == {0: 100, 1: 200, 2: 200}

    def test_single_step_mode(self, game):
        game.mode = ProgressionMode.SINGLE_STEP
        assert game.mode == ProgressionMode.SINGLE_STEP
        game.start_hand()
        act(game, ActionType.ALL_IN)
        act(game, ActionType.FOLD)
        act(game, ActionType.CALL)

        assert game.phase == HandPhase.PENDING_ADVANCE
        assert game.current_seat is None
        board_sizes = []
        while game.step_once():
            board_sizes.append(len(game.table.community_cards))
        assert board_sizes == [3, 4, 5, 5]
        assert game.is_hand_complete

    def test_snapshots_do_not_track_later_state(self, game):
        game.start_hand()
        br = game.betting_round
        player = game.table.get_player(0)
        act(game, ActionType.CALL)
        assert br.player_bet_amounts == {1: 5, 2: 10}  # snapshot from before the call
        assert player.stack == 1000
        assert game.betting_round.player_bet_amounts == {0: 10, 1: 5, 2: 10}
        assert game.table.get_player(0).stack == 990

    def test_table_reference_outlives_controller(self):
        game = pe.GameController(make_table(1000, 1000), 5, 10)
        game.start_hand()
        table = game.table
        del game
        assert table.total_pot == 15  # keep-alive holds the controller

    def test_random_play_conserves_chips(self):
        """Plays random legal actions through the bindings, as an AI loop would."""
        rng = random.Random(7)
        game = pe.GameController(make_table(500, 1200, 80, 1000, 300, 2000), 5, 10)
        game.table.deck.seed(7)
        start = total_chips(game)

        for _ in range(100):
            if sum(p.has_chips for p in game.table.get_all_players()) < 2:
                break
            game.mode = rng.choice([ProgressionMode.AUTO, ProgressionMode.SINGLE_STEP])
            game.start_hand()
            while not game.is_hand_complete:
                if game.step_once():
                    continue
                legal = game.legal_actions()
                seat = legal.seat
                options = [pe.Action(ActionType.FOLD, seat)]
                if legal.can_check:
                    options.append(pe.Action(ActionType.CHECK, seat))
                if legal.can_call:
                    options.append(pe.Action(ActionType.CALL, seat))
                if legal.can_bet:
                    options.append(pe.Action(ActionType.BET, seat, rng.randint(legal.min_bet, legal.max_bet)))
                if legal.can_raise:
                    options.append(
                        pe.Action(ActionType.RAISE, seat, rng.randint(legal.min_raise, legal.max_raise))
                    )
                if legal.can_all_in:
                    options.append(pe.Action(ActionType.ALL_IN, seat))
                game.submit_action(rng.choice(options))
                assert total_chips(game) == start

            assert game.last_result.total_pot == sum(game.contributions.values())
            assert total_chips(game) == start
