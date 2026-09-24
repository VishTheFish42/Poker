"""Unit and integration tests for RLAgent (Task 5.2), using the real C++
engine (not mocks) so every produced action is checked against the
engine's own legality rules.
"""

import pytest
import torch

from poker_engine import ActionType
from src.poker.ai.action_space import AIAction
from src.poker.ai.replay_buffer import ReplayBuffer
from src.poker.ai.rl_agent import RLAgent
from src.poker.ai.runner import play_hand
from tests.engine_helpers import act, cards, check_or_call, make_controller


def make_ai_controller(num_players=3, stack=1000, sb=1, bb=2, agent_factory=None):
    """A controller (no hand started) plus `{seat: agent}` for every seat."""
    agent_factory = agent_factory or (lambda: RLAgent(deterministic=True))
    gc = make_controller(num_players=num_players, stack=stack, sb=sb, bb=bb, start=False)
    return gc, {seat: agent_factory() for seat in range(num_players)}


def force(agent, ai_action):
    """Make `agent` always pick `ai_action`, keeping the real log-prob/entropy."""
    original_choose = agent._choose
    agent._choose = lambda logits, mask: (ai_action,) + original_choose(logits, mask)[1:]


class TestConstruction:
    def test_rejects_non_positive_temperature(self):
        with pytest.raises(ValueError):
            RLAgent(temperature=0)
        with pytest.raises(ValueError):
            RLAgent(temperature=-1.0)

    def test_defaults_to_a_fresh_policy_network(self):
        agent = RLAgent()
        assert agent.policy is not None
        assert not agent.policy.training  # eval() mode by default


class TestSelectActionLegality:
    def test_returned_action_is_always_legal(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        agent = RLAgent()

        for _ in range(20):
            action = agent.select_action(gc, gc.current_seat)
            assert gc.validate_action(action) is None

    def test_masking_respected_when_only_passive_actions_are_legal(self):
        gc = make_controller(num_players=2, stack=1000, sb=1, bb=2)
        act(gc, ActionType.ALL_IN)  # seat 0 shoves; seat 1 can only fold or call, never bet/raise
        agent = RLAgent()

        for _ in range(20):
            action = agent.select_action(gc, gc.current_seat)
            assert gc.validate_action(action) is None
            assert action.action_type not in (ActionType.BET, ActionType.RAISE)

    def test_legal_action_on_the_flop_with_no_bet_yet(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        check_or_call(gc)
        check_or_call(gc)  # flop, no bet yet
        agent = RLAgent()

        action = agent.select_action(gc, gc.current_seat)
        assert gc.validate_action(action) is None

    def test_rejects_a_seat_that_is_not_on_the_clock(self):
        gc = make_controller(num_players=2)
        with pytest.raises(ValueError):
            RLAgent().select_action(gc, 1 - gc.current_seat)


class TestDeterministicMode:
    def test_same_state_yields_the_same_action_repeatedly(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        agent = RLAgent(deterministic=True)

        first = agent.select_action(gc, gc.current_seat)
        second = agent.select_action(gc, gc.current_seat)

        assert first == second


class TestFullHandIntegration:
    def test_all_ai_hand_plays_to_completion(self):
        gc, agents = make_ai_controller(num_players=3, sb=1, bb=2)
        play_hand(gc, agents)
        assert gc.is_hand_complete

    def test_no_exceptions_across_several_hands(self):
        gc, agents = make_ai_controller(
            num_players=3, stack=200, sb=5, bb=10, agent_factory=lambda: RLAgent(temperature=1.5)
        )
        for _ in range(5):
            if sum(p.has_chips for p in gc.table.get_all_players()) < 2:
                break
            play_hand(gc, agents)  # start_hand() rotates the button itself
            assert gc.is_hand_complete


class TestTrainingEnabled:
    def test_disabled_by_default(self):
        assert RLAgent().training_enabled is False

    def test_enabled_when_a_replay_buffer_is_attached(self):
        assert RLAgent(replay_buffer=ReplayBuffer()).training_enabled is True

    def test_update_without_a_buffer_raises(self):
        with pytest.raises(RuntimeError):
            RLAgent().update()


class TestRecordsExperienceWhileTraining:
    def test_select_action_records_a_pending_experience(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        buffer = ReplayBuffer()
        agent = RLAgent(replay_buffer=buffer)

        agent.select_action(gc, gc.current_seat)

        assert len(agent._pending) == 1
        assert len(buffer) == 0  # not pushed into the buffer until finish_hand()

    def test_no_recording_when_not_training(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        agent = RLAgent()

        agent.select_action(gc, gc.current_seat)

        assert agent._pending == []


class TestFinishHand:
    def test_pushes_one_experience_per_pending_action(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        buffer = ReplayBuffer()
        agent = RLAgent(replay_buffer=buffer)
        agent.select_action(gc, gc.current_seat)
        agent.select_action(gc, gc.current_seat)

        agent.finish_hand(base_reward=1.5)

        assert len(buffer) == 2
        assert agent._pending == []

    def test_experience_reward_matches_base_reward_for_non_fold_action(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        check_or_call(gc)
        check_or_call(gc)  # flop, no bet yet
        buffer = ReplayBuffer()
        agent = RLAgent(replay_buffer=buffer)
        # Force a non-FOLD decision so the reward can't include any
        # fold-strength shaping, regardless of what the untrained network prefers.
        force(agent, AIAction.CHECK_CALL)

        agent.select_action(gc, gc.current_seat)
        agent.finish_hand(base_reward=2.0)
        experiences = buffer.drain()

        assert experiences[0].reward == pytest.approx(2.0)

    def test_fold_strength_penalty_is_added_for_a_folded_strong_hand(self):
        # Seat 1 holds Kc Ks; the flop Qh Qd 2c gives it two pair, and it
        # acts first after the flop heads-up.
        gc = make_controller(num_players=2, sb=1, bb=2, stacked_cards=cards("3h 4d Kc Ks 8d Qh Qd 2c"))
        check_or_call(gc)
        check_or_call(gc)  # reach the flop
        assert gc.current_seat == 1

        buffer = ReplayBuffer()
        agent = RLAgent(replay_buffer=buffer)
        force(agent, AIAction.FOLD)  # exercise the fold-strength path deterministically

        agent.select_action(gc, 1)
        agent.finish_hand(base_reward=-0.2)
        experiences = buffer.drain()

        assert experiences[0].reward < -0.2  # base reward plus a negative strength penalty

    def test_noop_when_not_training(self):
        agent = RLAgent()

        agent.finish_hand(base_reward=1.0)  # should not raise

        assert agent._pending == []


class TestUpdate:
    def test_returns_none_for_empty_buffer(self):
        agent = RLAgent(replay_buffer=ReplayBuffer())
        assert agent.update() is None

    def test_update_changes_policy_parameters(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        buffer = ReplayBuffer()
        agent = RLAgent(replay_buffer=buffer)

        before = [p.clone() for p in agent.policy.parameters()]
        for _ in range(4):
            agent.select_action(gc, gc.current_seat)
        agent.finish_hand(base_reward=3.0)
        loss = agent.update()
        after = list(agent.policy.parameters())

        assert loss is not None
        assert any(not torch.equal(b, a) for b, a in zip(before, after))

    def test_update_clears_the_buffer(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        buffer = ReplayBuffer()
        agent = RLAgent(replay_buffer=buffer)
        agent.select_action(gc, gc.current_seat)
        agent.finish_hand(base_reward=1.0)

        agent.update()

        assert len(buffer) == 0

    def test_policy_returns_to_eval_mode_after_update(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        buffer = ReplayBuffer()
        agent = RLAgent(replay_buffer=buffer)
        agent.select_action(gc, gc.current_seat)
        agent.finish_hand(base_reward=1.0)

        agent.update()

        assert not agent.policy.training


class TestFullHandIntegrationWithTraining:
    def test_all_ai_training_hand_completes_and_can_be_finished(self):
        buffers = [ReplayBuffer() for _ in range(3)]
        agent_iter = iter([RLAgent(replay_buffer=b, deterministic=True) for b in buffers])
        gc, agents = make_ai_controller(num_players=3, sb=1, bb=2, agent_factory=lambda: next(agent_iter))
        play_hand(gc, agents)
        assert gc.is_hand_complete

        for agent in agents.values():
            agent.finish_hand(base_reward=0.0)
            agent.update()  # should not raise even with 0 or few experiences


class TestSaveAndLoad:
    def test_load_restores_identical_outputs(self, tmp_path):
        agent = RLAgent()
        checkpoint = tmp_path / "policy.pt"
        agent.save(checkpoint)

        loaded = RLAgent.load(checkpoint)

        for original, restored in zip(agent.policy.parameters(), loaded.policy.parameters()):
            assert torch.equal(original, restored)

    def test_load_forwards_kwargs_to_the_new_agent(self, tmp_path):
        agent = RLAgent()
        checkpoint = tmp_path / "policy.pt"
        agent.save(checkpoint)

        loaded = RLAgent.load(checkpoint, temperature=3.0, deterministic=True)

        assert loaded.temperature == 3.0
        assert loaded.deterministic is True

    def test_save_creates_parent_directories(self, tmp_path):
        agent = RLAgent()
        checkpoint = tmp_path / "nested" / "dir" / "policy.pt"

        agent.save(checkpoint)

        assert checkpoint.exists()

    def test_load_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            RLAgent.load(tmp_path / "does_not_exist.pt")

    def test_trained_weights_survive_a_round_trip(self, tmp_path):
        gc = make_controller(num_players=2, sb=1, bb=2)
        buffer = ReplayBuffer()
        agent = RLAgent(replay_buffer=buffer)
        for _ in range(3):
            agent.select_action(gc, gc.current_seat)
        agent.finish_hand(base_reward=1.0)
        agent.update()  # actually changes the weights from their random init

        checkpoint = tmp_path / "policy.pt"
        agent.save(checkpoint)
        loaded = RLAgent.load(checkpoint)

        for original, restored in zip(agent.policy.parameters(), loaded.policy.parameters()):
            assert torch.equal(original, restored)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
