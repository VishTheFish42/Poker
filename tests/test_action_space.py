"""Unit tests for the discrete AI action space (Task 5.1), using a real
GameController (not mocks) to prove masks/translations line up with what
the engine actually considers legal.
"""

import pytest

from src.poker.ai.action_space import ActionSpace, AIAction
from src.poker.engine.action import ActionType
from src.poker.engine.controller import GameController
from src.poker.engine.player import Player
from src.poker.engine.table import Table


def make_controller(num_players=3, stack=1000, sb=1, bb=2):
    table = Table(num_players)
    for seat in range(num_players):
        table.add_player(Player(f"P{seat}", seat, stack))
    gc = GameController(table, sb, bb)
    gc.start_new_hand()
    return gc


class TestSize:
    def test_size_matches_action_count(self):
        assert ActionSpace.size() == len(list(AIAction)) == 6


class TestLegalMask:
    def test_fold_always_legal(self):
        gc = make_controller()
        mask = ActionSpace.legal_mask(gc.get_legal_actions())
        assert mask[AIAction.FOLD.value] is True

    def test_facing_a_bet_allows_call_and_raise_not_bet(self):
        gc = make_controller(num_players=2, sb=1, bb=2)  # heads-up: SB owes the call
        legal = gc.get_legal_actions()
        mask = ActionSpace.legal_mask(legal)

        assert legal["can_call"] and not legal["can_check"]
        assert mask[AIAction.CHECK_CALL.value] is True
        assert mask[AIAction.BET_MIN.value] is True  # this is a raise, but shares the "open" slot
        assert mask[AIAction.ALL_IN.value] is True

    def test_opening_action_has_no_bet_owed(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        gc.check_or_call()  # SB calls
        gc.check_or_call()  # BB checks their option -> flop, no bet yet
        legal = gc.get_legal_actions()
        mask = ActionSpace.legal_mask(legal)

        assert legal["can_bet"]
        assert mask[AIAction.CHECK_CALL.value] is True  # check is legal
        assert mask[AIAction.BET_POT.value] is True

    def test_all_in_illegal_with_no_chips(self):
        gc = make_controller(num_players=2, stack=1000, sb=1, bb=2)
        legal = dict(gc.get_legal_actions())
        legal["can_all_in"] = False
        mask = ActionSpace.legal_mask(legal)
        assert mask[AIAction.ALL_IN.value] is False


class TestToEngineAction:
    def test_fold_translation(self):
        gc = make_controller(num_players=2)
        legal = gc.get_legal_actions()
        seat = gc.get_current_player().seat

        action = ActionSpace.to_engine_action(AIAction.FOLD, seat, legal, gc.table.total_pot)

        assert action.action_type == ActionType.FOLD
        assert action.player_seat == seat

    def test_check_call_checks_when_nothing_owed(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        gc.check_or_call()  # SB calls
        legal = gc.get_legal_actions()  # BB now owes nothing
        seat = gc.get_current_player().seat

        action = ActionSpace.to_engine_action(AIAction.CHECK_CALL, seat, legal, gc.table.total_pot)

        assert action.action_type == ActionType.CHECK

    def test_check_call_calls_the_owed_amount(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        legal = gc.get_legal_actions()
        seat = gc.get_current_player().seat

        action = ActionSpace.to_engine_action(AIAction.CHECK_CALL, seat, legal, gc.table.total_pot)

        assert action.action_type == ActionType.CALL
        assert action.amount == legal["call_amount"]

    def test_check_call_goes_all_in_when_call_exceeds_stack(self):
        gc = make_controller(num_players=2, stack=1000, sb=1, bb=2)
        gc.go_all_in()  # seat 0 (button/SB) shoves preflop
        legal = gc.get_legal_actions()  # seat 1 (BB) now faces a call for their entire remaining stack
        seat = gc.get_current_player().seat

        action = ActionSpace.to_engine_action(AIAction.CHECK_CALL, seat, legal, gc.table.total_pot)

        assert action.action_type == ActionType.ALL_IN
        assert action.amount == legal["max_bet"]

    def test_all_in_uses_full_stack(self):
        gc = make_controller(num_players=2, stack=500)
        legal = gc.get_legal_actions()
        seat = gc.get_current_player().seat

        action = ActionSpace.to_engine_action(AIAction.ALL_IN, seat, legal, gc.table.total_pot)

        assert action.action_type == ActionType.ALL_IN
        assert action.amount == legal["max_bet"]

    def test_bet_min_uses_min_bound_when_opening(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        gc.check_or_call()
        gc.check_or_call()  # reach the flop, no bet yet
        legal = gc.get_legal_actions()
        seat = gc.get_current_player().seat
        assert legal["can_bet"]

        action = ActionSpace.to_engine_action(AIAction.BET_MIN, seat, legal, gc.table.total_pot)

        assert action.action_type == ActionType.BET
        assert action.amount == legal["min_bet"]

    def test_bet_pot_is_clamped_to_legal_bounds(self):
        gc = make_controller(num_players=2, stack=1000, sb=1, bb=2)
        gc.check_or_call()
        gc.check_or_call()  # flop, pot is small relative to stacks
        legal = gc.get_legal_actions()
        seat = gc.get_current_player().seat
        pot = gc.table.total_pot

        action = ActionSpace.to_engine_action(AIAction.BET_POT, seat, legal, pot)

        assert legal["min_bet"] <= action.amount <= legal["max_bet"]

    def test_raise_used_when_a_bet_is_already_live(self):
        gc = make_controller(num_players=2, sb=1, bb=2)  # SB owes the BB's preflop bet
        legal = gc.get_legal_actions()
        seat = gc.get_current_player().seat
        assert legal["can_raise"]

        action = ActionSpace.to_engine_action(AIAction.BET_MIN, seat, legal, gc.table.total_pot)

        assert action.action_type == ActionType.RAISE
        assert action.amount == legal["min_raise"]

    def test_illegal_action_raises(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        legal = dict(gc.get_legal_actions())
        legal["can_all_in"] = False
        seat = gc.get_current_player().seat

        with pytest.raises(ValueError):
            ActionSpace.to_engine_action(AIAction.ALL_IN, seat, legal, gc.table.total_pot)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
