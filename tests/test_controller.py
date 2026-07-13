"""Unit and integration tests for GameController round progression."""

import pytest

from src.poker.engine.action import Action, ActionType
from src.poker.engine.controller import GameController
from src.poker.engine.player import AIPlayer, HumanPlayer, Player, PlayerStatus
from src.poker.engine.table import GameState, Table


class CallStationAgent:
    """Fake agent for testing auto_advance(): checks if possible, otherwise
    calls the amount owed. Never folds or raises. Reacts to game_state's
    legal_actions, so (unlike a hardcoded action) it stays valid across
    streets - a real placeholder policy would behave the same way.
    """

    def select_action(self, game_state, player):
        legal = game_state["legal_actions"]
        if legal["can_check"]:
            return Action(ActionType.CHECK, player.seat)
        return Action(ActionType.CALL, player.seat, legal["call_amount"])


class FoldingAgent:
    """Fake agent that always folds - always legal regardless of street."""

    def select_action(self, game_state, player):
        return Action(ActionType.FOLD, player.seat)


def make_controller(num_players=3, stack=1000, sb=1, bb=2, num_seats=None):
    table = Table(num_seats or num_players)
    players = [Player("P" + str(i), i, stack) for i in range(num_players)]
    for p in players:
        table.add_player(p)
    return GameController(table, sb, bb), table, players


def call_or_check(gc, seat):
    """Helper: call the current amount owed, or check if nothing is owed."""
    amt = gc.betting_round.get_amount_to_call(seat)
    action = Action(ActionType.CALL, seat, amt) if amt > 0 else Action(ActionType.CHECK, seat)
    gc.submit_action(action)


class TestStartNewHand:
    def test_first_hand_sets_up_blinds_and_deals(self):
        gc, table, players = make_controller()
        gc.start_new_hand()

        assert table.button_seat == 0
        assert table.small_blind_seat == 1
        assert table.big_blind_seat == 2
        assert table.small_blind_amount == 1
        assert table.big_blind_amount == 2
        for p in players:
            assert len(p.hole_cards) == 2
        assert players[1].stack == 999  # posted SB
        assert players[2].stack == 998  # posted BB

    def test_preflop_action_starts_utg(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        # 3-handed: UTG is the seat after the big blind, which wraps to the button/seat 0.
        assert gc.get_current_player().seat == 0

    def test_custom_blind_amounts_used_on_first_hand(self):
        gc, table, players = make_controller(stack=5000, sb=25, bb=50)
        gc.start_new_hand()
        assert players[1].stack == 4975
        assert players[2].stack == 4950


class TestRoundProgression:
    def test_full_hand_checks_through_to_showdown(self):
        gc, table, players = make_controller()
        gc.start_new_hand()

        # Pre-flop: everyone calls/checks.
        call_or_check(gc, 0)  # UTG/button calls the BB
        call_or_check(gc, 1)  # SB calls
        call_or_check(gc, 2)  # BB checks its option
        assert table.game_state == GameState.FLOP
        assert len(table.community_cards) == 3

        # Flop, turn, river: check around each time.
        for expected_state, expected_cards in [
            (GameState.TURN, 4),
            (GameState.RIVER, 5),
            (GameState.HAND_COMPLETE, 5),
        ]:
            for _ in range(3):
                seat = gc.get_current_player().seat
                call_or_check(gc, seat)
            assert table.game_state == expected_state
            assert len(table.community_cards) == expected_cards

        assert gc.is_hand_complete
        assert gc.last_result is not None
        assert gc.last_result.is_showdown
        assert sum(r.chips_won for r in gc.last_result.player_results) == 6  # 2+2+2 preflop
        assert sum(p.stack for p in players) == 3000  # chips conserved

    def test_turn_order_enforced(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        current = gc.get_current_player().seat
        wrong_seat = (current + 1) % 3
        with pytest.raises(ValueError):
            gc.submit_action(Action(ActionType.FOLD, wrong_seat))

    def test_fold_out_ends_hand_without_full_board(self):
        gc, table, players = make_controller()
        gc.start_new_hand()

        first = gc.get_current_player().seat
        gc.submit_action(Action(ActionType.RAISE, first, 4))
        second = gc.get_current_player().seat
        gc.submit_action(Action(ActionType.FOLD, second))
        third = gc.get_current_player().seat
        gc.submit_action(Action(ActionType.FOLD, third))

        assert gc.is_hand_complete
        assert not gc.last_result.is_showdown
        assert gc.get_current_player() is None
        winner = gc.last_result.player_results[0]
        assert winner.seat == first
        assert sum(p.stack for p in players) == 3000  # chips conserved


class TestAllInRunout:
    def test_all_players_all_in_preflop_runs_out_board_automatically(self):
        gc, table, players = make_controller(stack=10)  # everyone effectively shoves
        gc.start_new_hand()

        # UTG/button shoves; SB and BB call with their whole remaining stacks.
        first = gc.get_current_player().seat
        gc.submit_action(Action(ActionType.ALL_IN, first, players[first].stack))
        second = gc.get_current_player().seat
        call_or_check(gc, second)
        third = gc.get_current_player().seat
        call_or_check(gc, third)

        # No one has chips left to act with, so the board should run out
        # automatically straight through to showdown.
        assert gc.is_hand_complete
        assert gc.last_result.is_showdown
        assert len(table.community_cards) == 5
        assert sum(p.stack for p in players) == 30  # chips conserved

    def test_side_pot_all_in_for_less(self):
        table = Table(3)
        players = [Player("P" + str(i), i, 1000) for i in range(3)]
        for p in players:
            table.add_player(p)
        players[0].stack = 10  # short stack

        gc = GameController(table, 1, 2)
        gc.start_new_hand()

        first = gc.get_current_player().seat  # seat 0 (short stack), UTG
        assert first == 0
        gc.submit_action(Action(ActionType.ALL_IN, 0, players[0].stack))
        second = gc.get_current_player().seat
        gc.submit_action(Action(ActionType.FOLD, second))
        third = gc.get_current_player().seat
        gc.submit_action(Action(ActionType.FOLD, third))

        # Only one player remains (the other two folded) - immediate fold win,
        # no board should be forced out.
        assert gc.is_hand_complete
        assert not gc.last_result.is_showdown
        assert sum(p.stack for p in players) == 2010  # 10 + 1000 + 1000 starting chips


class TestButtonRotation:
    def test_rotate_button_and_preserve_blinds_across_hands(self):
        gc, table, players = make_controller(num_players=3, sb=5, bb=10)
        gc.start_new_hand()
        assert table.button_seat == 0

        # Fold the hand out immediately to reach HAND_COMPLETE.
        first = gc.get_current_player().seat
        gc.submit_action(Action(ActionType.RAISE, first, 10))  # min raise is the $10 BB
        second = gc.get_current_player().seat
        gc.submit_action(Action(ActionType.FOLD, second))
        third = gc.get_current_player().seat
        gc.submit_action(Action(ActionType.FOLD, third))
        assert gc.is_hand_complete

        gc.start_new_hand()
        assert table.button_seat == 1
        assert table.small_blind_seat == 2
        assert table.big_blind_seat == 0
        assert table.small_blind_amount == 5
        assert table.big_blind_amount == 10

    def test_busted_player_skipped_by_future_button_and_blinds(self):
        """A player who busts out (stack hits 0) must not receive the
        button or a blind in subsequent hands - they're sitting out, not
        an empty gap that raw seat arithmetic would still assign to.
        """
        gc, table, players = make_controller(num_players=4)
        gc.start_new_hand()

        # Force seat 1 to bust by draining its stack, as if it lost an all-in.
        players[1].stack = 0

        gc.start_new_hand()

        assert table.get_player(1).status == PlayerStatus.SITTING_OUT
        assert table.button_seat != 1
        assert table.small_blind_seat != 1
        assert table.big_blind_seat != 1
        # The three remaining players should be the only ones in the hand.
        assert len(table.get_players_in_hand()) == 3
        assert all(p.seat != 1 for p in table.get_players_in_hand())


class TestConvenienceActions:
    """Task 3.2: ergonomic fold/check-call/bet/raise verbs on GameController."""

    def test_fold_acts_for_current_player(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        current = gc.get_current_player().seat

        gc.fold()

        assert table.get_player(current).status == PlayerStatus.FOLDED

    def test_check_or_call_checks_when_nothing_owed(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        gc.check_or_call()  # UTG calls the BB
        gc.check_or_call()  # SB calls
        bb_seat = gc.get_current_player().seat
        bb_stack_before = table.get_player(bb_seat).stack

        gc.check_or_call()  # BB's option: should CHECK, not spend chips

        assert table.get_player(bb_seat).stack == bb_stack_before
        assert table.game_state == GameState.FLOP

    def test_check_or_call_calls_the_owed_amount(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        utg_seat = gc.get_current_player().seat
        stack_before = table.get_player(utg_seat).stack

        gc.check_or_call()

        assert table.get_player(utg_seat).stack == stack_before - 2  # called the BB

    def test_check_or_call_goes_all_in_for_a_short_stack(self):
        table = Table(3)
        players = [Player("P" + str(i), i, 1000) for i in range(3)]
        for p in players:
            table.add_player(p)
        players[0].stack = 1  # UTG can't fully call the BB

        gc = GameController(table, 1, 2)
        gc.start_new_hand()
        assert gc.get_current_player().seat == 0

        gc.check_or_call()

        assert players[0].stack == 0
        assert players[0].status == PlayerStatus.ALL_IN

    def test_bet_and_raise_by(self):
        gc, table, players = make_controller()
        gc.start_new_hand()

        # Preflop: UTG calls, SB calls, BB uses its option to raise.
        gc.check_or_call()
        gc.check_or_call()
        bb_seat = gc.get_current_player().seat
        gc.raise_by(10)
        assert gc.betting_round.highest_bet == 12  # $2 blind + $10 raise
        assert not gc.betting_round._is_round_complete()

        # Everyone folds to the raiser.
        gc.fold()
        gc.fold()
        assert gc.is_hand_complete
        assert gc.last_result.player_results[0].seat == bb_seat

    def test_bet_on_a_fresh_street(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        gc.check_or_call()
        gc.check_or_call()
        gc.check_or_call()
        assert table.game_state == GameState.FLOP

        first = gc.get_current_player().seat
        stack_before = table.get_player(first).stack
        gc.bet(20)

        assert table.get_player(first).stack == stack_before - 20
        assert gc.betting_round.highest_bet == 20

    def test_go_all_in(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        seat = gc.get_current_player().seat

        gc.go_all_in()

        assert table.get_player(seat).stack == 0
        assert table.get_player(seat).status == PlayerStatus.ALL_IN

    def test_no_current_player_raises(self):
        gc, table, players = make_controller()
        with pytest.raises(RuntimeError):
            gc.fold()


class TestLegalActions:
    """Task 3.2: legal-action introspection for driving a UI or AI."""

    def test_facing_a_bet_can_fold_call_raise_not_check_or_bet(self):
        gc, table, players = make_controller()
        gc.start_new_hand()  # UTG faces the $2 BB

        legal = gc.get_legal_actions()

        assert legal["can_fold"] is True
        assert legal["can_check"] is False
        assert legal["can_call"] is True
        assert legal["call_amount"] == 2
        assert legal["can_bet"] is False
        assert legal["can_raise"] is True
        assert legal["min_raise"] == 2
        assert legal["max_raise"] == 998
        assert legal["can_all_in"] is True

    def test_big_blind_option_can_check_or_raise_not_call_or_bet(self):
        """The BB's preflop option is a RAISE in poker terms (its posted
        blind is already a live wager), even though call_amount is 0.
        """
        gc, table, players = make_controller()
        gc.start_new_hand()
        gc.check_or_call()  # UTG calls
        gc.check_or_call()  # SB calls

        legal = gc.get_legal_actions()  # BB's option

        assert legal["can_check"] is True
        assert legal["can_call"] is False
        assert legal["call_amount"] == 0
        assert legal["can_bet"] is False
        assert legal["can_raise"] is True
        assert legal["min_raise"] == 2  # min_raise_amount carried from the blind

    def test_fresh_street_can_check_or_bet(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        gc.check_or_call()
        gc.check_or_call()
        gc.check_or_call()
        assert table.game_state == GameState.FLOP

        legal = gc.get_legal_actions()

        assert legal["can_check"] is True
        assert legal["can_bet"] is True
        assert legal["can_raise"] is False

    def test_short_stack_cannot_call_only_all_in(self):
        table = Table(3)
        players = [Player("P" + str(i), i, 1000) for i in range(3)]
        for p in players:
            table.add_player(p)
        players[0].stack = 1  # UTG can't cover the $2 call

        gc = GameController(table, 1, 2)
        gc.start_new_hand()

        legal = gc.get_legal_actions()

        assert legal["can_call"] is False
        assert legal["can_all_in"] is True

    def test_no_current_player_raises(self):
        gc, table, players = make_controller()
        with pytest.raises(RuntimeError):
            gc.get_legal_actions()


class TestHumanPlayerIntegration:
    """Task 3.2: HumanPlayer.action_required tracks whose turn needs UI input."""

    def test_action_required_set_for_human_on_the_clock(self):
        table = Table(3)
        players = [HumanPlayer("H" + str(i), i, 1000) for i in range(3)]
        for p in players:
            table.add_player(p)
        gc = GameController(table, 1, 2)

        gc.start_new_hand()
        current = gc.get_current_player()

        assert current.action_required is True
        others = [p for p in players if p.seat != current.seat]
        assert all(not p.action_required for p in others)

    def test_action_required_moves_to_next_human_after_action(self):
        table = Table(3)
        players = [HumanPlayer("H" + str(i), i, 1000) for i in range(3)]
        for p in players:
            table.add_player(p)
        gc = GameController(table, 1, 2)
        gc.start_new_hand()

        acting = gc.get_current_player()
        gc.check_or_call()
        next_player = gc.get_current_player()

        assert acting.action_required is False
        assert next_player.action_required is True


class TestHeadsUpTurnOrder:
    """Task 3.3: heads-up (2-player) turn order follows the standard rule -
    button acts first pre-flop, non-button acts first post-flop.
    """

    def test_button_acts_first_preflop_heads_up(self):
        gc, table, players = make_controller(num_players=2, num_seats=2)
        gc.start_new_hand()

        assert table.small_blind_seat == table.button_seat  # button posts SB
        assert gc.get_current_player().seat == table.button_seat

    def test_non_button_acts_first_postflop_heads_up(self):
        gc, table, players = make_controller(num_players=2, num_seats=2)
        gc.start_new_hand()

        gc.check_or_call()  # button/SB calls
        gc.check_or_call()  # BB checks its option
        assert table.game_state == GameState.FLOP

        assert gc.get_current_player().seat != table.button_seat

    def test_button_alternates_each_hand_heads_up(self):
        gc, table, players = make_controller(num_players=2, num_seats=2, sb=1, bb=2)
        gc.start_new_hand()
        first_button = table.button_seat
        gc.fold()  # end hand quickly
        assert gc.is_hand_complete

        gc.start_new_hand()
        assert table.button_seat != first_button
        assert table.small_blind_seat == table.button_seat


class TestValidateAction:
    """Task 3.3: validate_action() is a non-mutating dry-run check."""

    def test_legal_action_returns_none(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        seat = gc.get_current_player().seat

        assert gc.validate_action(Action(ActionType.FOLD, seat)) is None

    def test_does_not_mutate_state(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        seat = gc.get_current_player().seat
        stack_before = table.get_player(seat).stack
        pot_before = table.total_pot

        gc.validate_action(Action(ActionType.CALL, seat, 2))

        assert table.get_player(seat).stack == stack_before
        assert table.total_pot == pot_before
        assert table.get_player(seat).status == PlayerStatus.ACTIVE
        assert gc.get_current_player().seat == seat  # turn hasn't advanced

    def test_wrong_seat_rejected(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        wrong_seat = (gc.get_current_player().seat + 1) % 3

        reason = gc.validate_action(Action(ActionType.FOLD, wrong_seat))

        assert reason is not None
        assert "turn" in reason

    def test_check_rejected_when_amount_owed(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        seat = gc.get_current_player().seat  # UTG faces the BB

        reason = gc.validate_action(Action(ActionType.CHECK, seat))

        assert reason is not None

    def test_bet_out_of_range_rejected(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        gc.check_or_call()
        gc.check_or_call()
        seat = gc.get_current_player().seat  # BB's option -> raise, not bet

        too_small = gc.validate_action(Action(ActionType.RAISE, seat, 1))
        too_big = gc.validate_action(Action(ActionType.RAISE, seat, 100000))
        valid = gc.validate_action(Action(ActionType.RAISE, seat, 10))

        assert too_small is not None
        assert too_big is not None
        assert valid is None

    def test_submit_action_raises_with_validate_action_reason(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        seat = gc.get_current_player().seat

        with pytest.raises(ValueError):
            gc.submit_action(Action(ActionType.CHECK, seat))  # can't check facing the BB


class TestIncompleteRaiseCap:
    """An incomplete (short) all-in raise must not reopen re-raising rights
    for players who already matched the previous bet - only call or fold.
    """

    def test_capped_player_cannot_raise_via_convenience_or_legal_actions(self):
        table = Table(4)
        players = [Player("P" + str(i), i, 1000) for i in range(4)]
        for p in players:
            table.add_player(p)
        gc = GameController(table, 50, 100)
        gc.start_new_hand()

        utg = gc.get_current_player().seat
        gc.check_or_call()  # UTG calls the $100 BB

        button = gc.get_current_player().seat
        players[button].stack = 150  # can only shove for an incomplete $50 raise
        gc.go_all_in()

        # SB and BB haven't acted yet this round - they must go before turn
        # order comes back around to UTG.
        gc.fold()  # SB
        gc.fold()  # BB

        # Now it's UTG's turn again, facing the extra $50 - they're capped.
        assert gc.get_current_player().seat == utg
        legal = gc.get_legal_actions()
        assert legal["can_raise"] is False
        assert legal["can_call"] is True

        with pytest.raises(ValueError):
            gc.raise_by(200)

        # Calling is still fine. With only UTG and the all-in button left,
        # the hand should run the board out automatically to showdown
        # (nobody left who could respond to further betting).
        gc.check_or_call()
        assert gc.is_hand_complete
        assert gc.last_result.is_showdown
        assert len(table.community_cards) == 5
        assert sum(p.stack for p in players) == 3150  # 3x$1000 + button's $150 stack


class TestAutoAdvance:
    """Task 3.4: automatically drive the hand through any player whose
    action is already available (staged human choice or AI agent), without
    the caller having to notice and push it through manually.
    """

    def test_generic_player_does_not_auto_advance(self):
        """A plain Player (no get_action() override worth calling) must
        stop and wait for external submit_action(), not error or hang.
        """
        gc, table, players = make_controller()
        gc.start_new_hand()
        seat_before = gc.get_current_player().seat

        gc.auto_advance()

        assert gc.get_current_player().seat == seat_before
        assert not gc.is_hand_complete

    def test_human_with_no_staged_action_stops(self):
        table = Table(3)
        players = [HumanPlayer("H" + str(i), i, 1000) for i in range(3)]
        for p in players:
            table.add_player(p)
        gc = GameController(table, 1, 2)
        gc.start_new_hand()
        seat_before = gc.get_current_player().seat

        gc.auto_advance()  # nobody has staged an action yet

        assert gc.get_current_player().seat == seat_before

    def test_human_staged_action_is_consumed_and_advances(self):
        table = Table(3)
        players = [HumanPlayer("H" + str(i), i, 1000) for i in range(3)]
        for p in players:
            table.add_player(p)
        gc = GameController(table, 1, 2)
        gc.start_new_hand()
        acting = gc.get_current_player()

        acting.set_action(Action(ActionType.FOLD, acting.seat))
        gc.auto_advance()

        assert acting.status == PlayerStatus.FOLDED
        assert gc.get_current_player().seat != acting.seat
        # The consumed action must not linger for next time.
        assert acting.pending_action is None

    def test_ai_chain_plays_through_to_human(self):
        """Consecutive AI turns with agents assigned should play out
        automatically, stopping only once a human (with nothing staged)
        is on the clock again.
        """
        table = Table(3)
        human = HumanPlayer("Hero", 0, 1000)
        ai1 = AIPlayer("Bot1", 1, 1000)
        ai2 = AIPlayer("Bot2", 2, 1000)
        ai1.set_agent(CallStationAgent())
        ai2.set_agent(CallStationAgent())
        for p in (human, ai1, ai2):
            table.add_player(p)
        gc = GameController(table, 1, 2)

        gc.start_new_hand()  # start_new_hand() itself calls auto_advance()

        # Preflop: UTG is seat 0 (human) in this 3-handed table - it should
        # stop immediately without consulting either AI yet.
        assert gc.get_current_player().seat == 0

        human.set_action(Action(ActionType.CALL, 0, gc.betting_round.get_amount_to_call(0)))
        gc.auto_advance()

        # Preflop completes automatically (SB calls, BB checks its option),
        # the flop is dealt, and both AIs check around on the fresh street
        # too - stopping only once it wraps back around to the human.
        assert table.game_state == GameState.FLOP
        assert gc.get_current_player().seat == 0
        assert not gc.is_hand_complete

    def test_ai_without_agent_stops_and_waits(self):
        table = Table(2)
        human = HumanPlayer("Hero", 0, 1000)
        ai = AIPlayer("Bot", 1, 1000)  # no agent assigned
        table.add_player(human)
        table.add_player(ai)
        gc = GameController(table, 1, 2)
        gc.start_new_hand()

        # Heads-up: button (seat 0, human) posts SB and acts first preflop.
        assert gc.get_current_player().seat == 0
        human.set_action(Action(ActionType.CALL, 0, gc.betting_round.get_amount_to_call(0)))
        gc.auto_advance()

        # It's now the AI's turn (BB option), but it has no agent - must
        # stop and wait rather than raising or hanging.
        assert gc.get_current_player().seat == 1
        assert not gc.is_hand_complete

    def test_convenience_methods_auto_advance_afterward(self):
        """fold()/check_or_call()/etc. should chain into auto_advance() so
        subsequent AI-with-agent turns play out without an extra call.
        """
        table = Table(3)
        human = HumanPlayer("Hero", 0, 1000)
        ai1 = AIPlayer("Bot1", 1, 1000)
        ai2 = AIPlayer("Bot2", 2, 1000)
        ai1.set_agent(FoldingAgent())
        ai2.set_agent(FoldingAgent())
        for p in (human, ai1, ai2):
            table.add_player(p)
        gc = GameController(table, 1, 2)
        gc.start_new_hand()
        assert gc.get_current_player().seat == 0

        gc.check_or_call()  # human calls; both AIs should auto-fold after

        assert gc.is_hand_complete
        assert not gc.last_result.is_showdown
        assert gc.last_result.player_results[0].seat == 0


class TestActionPrompt:
    """Task 3.5: human-readable prompt describing the current decision."""

    def test_none_when_no_one_on_the_clock(self):
        gc, table, players = make_controller()
        assert gc.get_action_prompt() is None

    def test_none_after_hand_complete(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        gc.fold()
        gc.fold()
        assert gc.is_hand_complete
        assert gc.get_action_prompt() is None

    def test_prompt_includes_name_hand_pot_and_options(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        seat = gc.get_current_player().seat
        prompt = gc.get_action_prompt()

        assert players[seat].name in prompt
        assert "Pot: $3" in prompt
        assert "fold" in prompt
        assert "call $2" in prompt
        assert "raise" in prompt
        assert "check" not in prompt  # facing the BB, can't check
        assert "bet " not in prompt  # not a fresh-street bet opportunity

    def test_prompt_reflects_big_blind_option(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        gc.check_or_call()
        gc.check_or_call()

        prompt = gc.get_action_prompt()

        assert "check" in prompt
        assert "raise" in prompt
        assert "call" not in prompt  # BB already matched via its blind

    def test_prompt_reflects_fresh_street(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        gc.check_or_call()
        gc.check_or_call()
        gc.check_or_call()
        assert table.game_state == GameState.FLOP

        prompt = gc.get_action_prompt()

        assert "check" in prompt
        assert "bet " in prompt
        assert "raise" not in prompt


class TestIsWaitingForHuman:
    def test_true_for_human_with_action_required(self):
        table = Table(3)
        players = [HumanPlayer("H" + str(i), i, 1000) for i in range(3)]
        for p in players:
            table.add_player(p)
        gc = GameController(table, 1, 2)
        gc.start_new_hand()

        assert gc.is_waiting_for_human() is True

    def test_false_for_generic_player(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        assert gc.is_waiting_for_human() is False

    def test_false_once_staged_and_consumed(self):
        table = Table(3)
        players = [HumanPlayer("H" + str(i), i, 1000) for i in range(3)]
        for p in players:
            table.add_player(p)
        gc = GameController(table, 1, 2)
        gc.start_new_hand()
        acting = gc.get_current_player()

        acting.set_action(Action(ActionType.FOLD, acting.seat))
        assert gc.is_waiting_for_human() is False  # cleared as soon as staged

        gc.auto_advance()
        assert gc.is_waiting_for_human() is True  # now it's the next human's turn


class TestGameLog:
    """Task 3.5: automatic, human-readable event log of everything that happens."""

    def test_hand_header_and_blinds_logged(self):
        gc, table, players = make_controller()
        gc.start_new_hand()

        assert any("Hand #1" in line and players[0].name in line for line in gc.log)
        assert any(f"{players[1].name} posts small blind $1" in line for line in gc.log)
        assert any(f"{players[2].name} posts big blind $2" in line for line in gc.log)

    def test_actions_logged_with_names_and_amounts(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        gc.check_or_call()  # UTG calls $2
        gc.fold()  # SB folds
        gc.check_or_call()  # BB checks its option

        assert any(f"{players[0].name} calls $2" in line for line in gc.log)
        assert any(f"{players[1].name} folds" in line for line in gc.log)
        assert any(f"{players[2].name} checks" in line for line in gc.log)

    def test_all_in_suffix_logged(self):
        table = Table(3)
        players = [Player("P" + str(i), i, 1000) for i in range(3)]
        for p in players:
            table.add_player(p)
        players[0].stack = 1  # UTG can't cover the $2 call, must go all-in for $1
        gc = GameController(table, 1, 2)
        gc.start_new_hand()

        gc.check_or_call()  # routes to an all-in for the whole $1 stack

        assert any("goes all-in for $1" in line for line in gc.log)

    def test_all_in_suffix_on_a_plain_call(self):
        """A raw CALL that happens to exactly exhaust the stack should log
        as a call with an "and is all-in" suffix, not the ALL_IN wording -
        check_or_call() itself chooses to route exact-stack calls through
        ALL_IN, but submit_action(CALL) directly is still legal and should
        describe itself accurately.
        """
        table = Table(3)
        players = [Player("P" + str(i), i, 1000) for i in range(3)]
        for p in players:
            table.add_player(p)
        players[0].stack = 2  # exactly enough to call the $2 BB
        gc = GameController(table, 1, 2)
        gc.start_new_hand()

        gc.submit_action(Action(ActionType.CALL, 0, 2))

        assert any("calls $2 and is all-in" in line for line in gc.log)

    def test_street_transitions_logged(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        gc.check_or_call()
        gc.check_or_call()
        gc.check_or_call()

        assert any(line.startswith("-- Flop:") for line in gc.log)

    def test_showdown_result_logged(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        for _ in range(3):
            gc.check_or_call()  # preflop
        for _ in range(3):
            gc.check_or_call()  # flop
        for _ in range(3):
            gc.check_or_call()  # turn
        for _ in range(3):
            gc.check_or_call()  # river

        assert gc.is_hand_complete
        assert any("shows" in line for line in gc.log)
        assert any("wins $" in line for line in gc.log)

    def test_fold_win_logged_as_uncontested(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        gc.fold()
        gc.fold()

        assert any("wins the pot uncontested" in line for line in gc.log)

    def test_log_persists_and_hand_number_increments_across_hands(self):
        gc, table, players = make_controller()
        gc.start_new_hand()
        gc.fold()
        gc.fold()
        first_hand_log_length = len(gc.log)

        gc.start_new_hand()

        assert len(gc.log) > first_hand_log_length  # previous entries preserved
        assert any("Hand #2" in line for line in gc.log)
        assert gc.hand_number == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
