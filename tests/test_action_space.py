"""Unit tests for the discrete AI action space (Task 5.1), using the real
C++ engine (not mocks) to prove masks/translations line up with what the
engine actually considers legal.
"""

import pytest

from poker_engine import ActionType
from src.poker.ai.action_space import ActionSpace, AIAction
from tests.engine_helpers import act, check_or_call, make_controller


def lone_player_facing_all_in():
    """Heads-up flop where seat 1 has shoved and seat 0 (bigger stack) must
    respond: nobody is left to re-raise against, so only fold/call remain."""
    gc = make_controller(stacks=[2000, 1000], sb=1, bb=2)
    check_or_call(gc)  # seat 0 (button/SB) calls
    check_or_call(gc)  # seat 1 (BB) checks -> flop
    act(gc, ActionType.ALL_IN)  # seat 1 shoves
    return gc


class TestSize:
    def test_size_matches_action_count(self):
        assert ActionSpace.size() == len(list(AIAction)) == 6


class TestLegalMask:
    def test_fold_always_legal(self):
        gc = make_controller()
        mask = ActionSpace.legal_mask(gc.legal_actions())
        assert mask[AIAction.FOLD.value] is True

    def test_facing_a_bet_allows_call_and_raise(self):
        gc = make_controller(num_players=2, sb=1, bb=2)  # heads-up: SB owes the call
        legal = gc.legal_actions()
        mask = ActionSpace.legal_mask(legal)

        assert legal.can_call and not legal.can_check
        assert mask[AIAction.CHECK_CALL.value] is True
        assert mask[AIAction.BET_MIN.value] is True  # this is a raise, but shares the "open" slot
        assert mask[AIAction.ALL_IN.value] is True

    def test_opening_action_has_no_bet_owed(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        check_or_call(gc)
        check_or_call(gc)  # flop, no bet yet
        legal = gc.legal_actions()
        mask = ActionSpace.legal_mask(legal)

        assert legal.can_bet
        assert mask[AIAction.CHECK_CALL.value] is True  # check is legal
        assert mask[AIAction.BET_POT.value] is True

    def test_nothing_aggressive_when_no_opponent_can_respond(self):
        legal = lone_player_facing_all_in().legal_actions()
        mask = ActionSpace.legal_mask(legal)

        assert mask == [True, True, False, False, False, False]

    def test_calling_all_in_for_less_counts_as_check_call(self):
        gc = make_controller(stacks=[1000, 500], sb=1, bb=2)
        act(gc, ActionType.ALL_IN)  # seat 0 shoves 1000; seat 1 has only 498 behind
        legal = gc.legal_actions()
        mask = ActionSpace.legal_mask(legal)

        assert not legal.can_call and legal.can_all_in
        assert mask[AIAction.CHECK_CALL.value] is True


class TestToEngineAction:
    def test_fold_translation(self):
        gc = make_controller(num_players=2)
        legal = gc.legal_actions()

        action = ActionSpace.to_engine_action(AIAction.FOLD, legal, gc.table.total_pot)

        assert action.action_type == ActionType.FOLD
        assert action.player_seat == gc.current_seat

    def test_check_call_checks_when_nothing_owed(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        check_or_call(gc)  # SB calls; BB now owes nothing
        legal = gc.legal_actions()

        action = ActionSpace.to_engine_action(AIAction.CHECK_CALL, legal, gc.table.total_pot)

        assert action.action_type == ActionType.CHECK

    def test_check_call_calls_the_owed_amount(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        legal = gc.legal_actions()

        action = ActionSpace.to_engine_action(AIAction.CHECK_CALL, legal, gc.table.total_pot)

        assert action.action_type == ActionType.CALL
        assert action.amount == legal.call_amount

    def test_check_call_goes_all_in_when_call_exceeds_stack(self):
        gc = make_controller(stacks=[1000, 500], sb=1, bb=2)
        act(gc, ActionType.ALL_IN)  # seat 1 now faces a call bigger than its stack
        legal = gc.legal_actions()

        action = ActionSpace.to_engine_action(AIAction.CHECK_CALL, legal, gc.table.total_pot)

        assert action.action_type == ActionType.ALL_IN
        assert action.amount == legal.all_in_amount == 498
        assert gc.validate_action(action) is None

    def test_all_in_uses_full_stack(self):
        gc = make_controller(num_players=2, stack=500)
        legal = gc.legal_actions()

        action = ActionSpace.to_engine_action(AIAction.ALL_IN, legal, gc.table.total_pot)

        assert action.action_type == ActionType.ALL_IN
        assert action.amount == legal.all_in_amount == 499  # 500 minus the posted small blind

    def test_bet_min_uses_min_bound_when_opening(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        check_or_call(gc)
        check_or_call(gc)  # flop, no bet yet
        legal = gc.legal_actions()
        assert legal.can_bet

        action = ActionSpace.to_engine_action(AIAction.BET_MIN, legal, gc.table.total_pot)

        assert action.action_type == ActionType.BET
        assert action.amount == legal.min_bet

    def test_bet_pot_is_clamped_to_legal_bounds(self):
        gc = make_controller(num_players=2, stack=1000, sb=1, bb=2)
        check_or_call(gc)
        check_or_call(gc)  # flop, pot is small relative to stacks
        legal = gc.legal_actions()

        action = ActionSpace.to_engine_action(AIAction.BET_POT, legal, gc.table.total_pot)

        assert legal.min_bet <= action.amount <= legal.max_bet
        assert gc.validate_action(action) is None

    def test_raise_used_when_a_bet_is_already_live(self):
        gc = make_controller(num_players=2, sb=1, bb=2)  # SB owes the BB's preflop bet
        legal = gc.legal_actions()
        assert legal.can_raise

        action = ActionSpace.to_engine_action(AIAction.BET_MIN, legal, gc.table.total_pot)

        assert action.action_type == ActionType.RAISE
        assert action.amount == legal.min_raise

    def test_every_legal_choice_is_accepted_by_the_engine(self):
        gc = make_controller(num_players=3, sb=5, bb=10)
        legal = gc.legal_actions()
        for ai_action, is_legal in zip(ActionSpace.ACTIONS, ActionSpace.legal_mask(legal)):
            if is_legal:
                action = ActionSpace.to_engine_action(ai_action, legal, gc.table.total_pot)
                assert gc.validate_action(action) is None, ai_action

    def test_illegal_action_raises(self):
        gc = lone_player_facing_all_in()

        with pytest.raises(ValueError):
            ActionSpace.to_engine_action(AIAction.ALL_IN, gc.legal_actions(), gc.table.total_pot)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
