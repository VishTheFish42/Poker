"""Tests for the seat -> agent hand driver (poker.ai.runner), against the
real C++ engine."""

import pytest

from poker_engine import ActionType, HandPhase, ProgressionMode
from src.poker.ai.rl_agent import RLAgent
from src.poker.ai.runner import play_hand, run_ai_turns
from tests.engine_helpers import act, make_controller


def agents_for(*seats):
    return {seat: RLAgent(deterministic=True) for seat in seats}


class TestPlayHand:
    def test_plays_an_all_ai_hand_to_completion(self):
        gc = make_controller(num_players=3, sb=5, bb=10, start=False)

        result = play_hand(gc, agents_for(0, 1, 2))

        assert gc.is_hand_complete
        assert result.total_pot == sum(gc.contributions.values())
        assert sum(p.stack for p in gc.table.get_all_players()) == 3000

    def test_steps_through_pending_advances_in_single_step_mode(self):
        gc = make_controller(num_players=3, sb=5, bb=10, start=False)
        gc.mode = ProgressionMode.SINGLE_STEP

        play_hand(gc, agents_for(0, 1, 2))

        assert gc.is_hand_complete

    def test_seat_without_an_agent_raises(self):
        gc = make_controller(num_players=3, start=False)
        with pytest.raises(ValueError, match="seat 0"):
            play_hand(gc, agents_for(1, 2))  # seat 0 is under the gun
        assert gc.phase == HandPhase.AWAITING_ACTION

    def test_match_over_raises_runtime_error(self):
        gc = make_controller(stacks=[1000, 0], start=False)
        with pytest.raises(RuntimeError):
            play_hand(gc, agents_for(0, 1))


class TestRunAiTurns:
    def test_stops_for_a_seat_without_an_agent_and_resumes(self):
        gc = make_controller(num_players=3, sb=5, bb=10)  # seat 0 (UTG) is on the clock
        agents = agents_for(1, 2)

        assert run_ai_turns(gc, agents) == 0  # waits for the human at seat 0

        act(gc, ActionType.FOLD)  # the human acts, and is out of the hand

        assert run_ai_turns(gc, agents) is None  # the AI seats finish it
        assert gc.is_hand_complete

    def test_returns_none_for_a_completed_hand(self):
        gc = make_controller(num_players=2)
        act(gc, ActionType.FOLD)
        assert run_ai_turns(gc, {}) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
