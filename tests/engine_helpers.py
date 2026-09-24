"""Helpers for driving the real C++ engine (via `poker_engine`) in AI tests.

The bound engine is read-only from Python, so tests reach a given state by
playing to it - with `stacked_cards` fixing the deal where the cards matter.
Stacked cards deal two hole cards to each player in seat order, then burn +
flop, burn + turn, burn + river.
"""

import poker_engine as pe
from poker_engine import ActionType, HandPhase

_RANKS = {
    "2": pe.Rank.TWO, "3": pe.Rank.THREE, "4": pe.Rank.FOUR, "5": pe.Rank.FIVE,
    "6": pe.Rank.SIX, "7": pe.Rank.SEVEN, "8": pe.Rank.EIGHT, "9": pe.Rank.NINE,
    "T": pe.Rank.TEN, "J": pe.Rank.JACK, "Q": pe.Rank.QUEEN, "K": pe.Rank.KING, "A": pe.Rank.ACE,
}
_SUITS = {"s": pe.Suit.SPADES, "h": pe.Suit.HEARTS, "d": pe.Suit.DIAMONDS, "c": pe.Suit.CLUBS}


def cards(text):
    """Parse "As Kd 2c" into a list of `poker_engine.Card`s."""
    return [pe.Card(_SUITS[t[1]], _RANKS[t[0]]) for t in text.split()]


def make_controller(num_players=3, stack=1000, sb=1, bb=2, stacks=None, start=True, stacked_cards=()):
    """A controller with `num_players` seated (or one per entry in `stacks`).

    First hand: button 0. Heads-up the button posts the small blind and
    acts first pre-flop; 3+ handed, seat 1 is the small blind and seat 2
    the big blind.
    """
    stacks = stacks or [stack] * num_players
    table = pe.Table(len(stacks))
    for seat, chips in enumerate(stacks):
        table.add_player(pe.Player(f"P{seat}", seat, chips))
    controller = pe.GameController(table, sb, bb)
    if start:
        controller.start_hand(list(stacked_cards))
    return controller


def act(controller, action_type, amount=0):
    """Submit `action_type` for whoever is on the clock."""
    controller.submit_action(pe.Action(action_type, controller.current_seat, amount))


def check_or_call(controller):
    """Check if nothing is owed, otherwise call."""
    legal = controller.legal_actions()
    act(controller, ActionType.CHECK if legal.can_check else ActionType.CALL)


def check_down(controller):
    """Check/call every remaining decision until the hand ends."""
    while controller.phase == HandPhase.AWAITING_ACTION:
        check_or_call(controller)
