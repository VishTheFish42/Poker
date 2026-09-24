"""Unit and integration tests for OnlineTrainer (Task 5.4), using the real
C++ engine and real RLAgents (not mocks) so hand outcomes, rewards, and
policy updates are all exercised end to end.
"""

import pytest
import torch

from src.poker.ai.action_space import AIAction
from src.poker.ai.online_trainer import OnlineTrainer
from src.poker.ai.replay_buffer import ReplayBuffer
from src.poker.ai.rl_agent import RLAgent
from src.poker.ai.runner import play_hand, run_ai_turns
from tests.engine_helpers import make_controller


def make_training_game(num_players=3, stack=1000, sb=1, bb=2):
    """A controller (no hand started) with a training-enabled RLAgent per seat."""
    gc = make_controller(num_players=num_players, stack=stack, sb=sb, bb=bb, start=False)
    buffers = [ReplayBuffer() for _ in range(num_players)]
    agents = {seat: RLAgent(replay_buffer=buffers[seat], deterministic=True) for seat in range(num_players)}
    return gc, agents, buffers


def make_mixed_game(stack=1000, sb=1, bb=2):
    """Heads-up: seat 0 is a training AI forced to fold, seat 1 has no agent
    (e.g. a human). Seat 0 is the button, so it acts first pre-flop and its
    fold ends the hand before seat 1 ever needs to act."""
    gc = make_controller(num_players=2, stack=stack, sb=sb, bb=bb, start=False)
    agent = RLAgent(replay_buffer=ReplayBuffer(), deterministic=True)
    original_choose = agent._choose
    agent._choose = lambda logits, mask: (AIAction.FOLD,) + original_choose(logits, mask)[1:]
    return gc, {0: agent}


class TestProcessCompletedHand:
    def test_returns_empty_dict_when_no_result_yet(self):
        gc, agents, _ = make_training_game()
        trainer = OnlineTrainer()

        assert trainer.process_completed_hand(gc, agents) == {}

    def test_returns_a_reward_for_every_training_seat(self):
        gc, agents, _ = make_training_game(num_players=2)
        play_hand(gc, agents)
        trainer = OnlineTrainer()

        rewards = trainer.process_completed_hand(gc, agents)

        assert set(rewards.keys()) == {0, 1}
        assert all(isinstance(v, float) for v in rewards.values())

    def test_pushes_experiences_into_each_agents_buffer(self):
        gc, agents, buffers = make_training_game(num_players=2)
        play_hand(gc, agents)
        trainer = OnlineTrainer(hands_per_update=1000)  # avoid auto-update clearing buffers

        trainer.process_completed_hand(gc, agents)

        assert any(len(b) > 0 for b in buffers)

    def test_seat_without_an_agent_is_skipped(self):
        gc, agents = make_mixed_game()
        gc.start_hand()
        assert run_ai_turns(gc, agents) is None  # seat 0's fold ended the hand
        trainer = OnlineTrainer()

        rewards = trainer.process_completed_hand(gc, agents)

        assert set(rewards) == {0}

    def test_inference_only_agent_is_skipped(self):
        gc, agents, _ = make_training_game(num_players=2)
        agents[1] = RLAgent(deterministic=True)  # no replay buffer
        play_hand(gc, agents)

        rewards = OnlineTrainer().process_completed_hand(gc, agents)

        assert set(rewards) == {0}

    def test_folded_seat_gets_its_lost_contribution_as_reward(self):
        gc, agents = make_mixed_game(sb=5, bb=10)
        gc.start_hand()
        run_ai_turns(gc, agents)  # seat 0 folds its posted small blind

        rewards = OnlineTrainer(hands_per_update=1000).process_completed_hand(gc, agents)

        assert rewards[0] == pytest.approx(-5 / 10)


class TestPeriodicUpdate:
    def test_update_not_triggered_before_hands_per_update(self):
        gc, agents, buffers = make_training_game(num_players=2)
        play_hand(gc, agents)
        trainer = OnlineTrainer(hands_per_update=2)

        trainer.process_completed_hand(gc, agents)

        assert any(len(b) > 0 for b in buffers)  # still sitting there, unconsumed

    def test_update_triggered_after_hands_per_update(self):
        # Deliberately processes the same completed hand twice rather than
        # dealing a second one: a heads-up deterministic policy can bust a
        # player in a single hand, which would leave too few players with
        # chips for start_hand() to deal to. This test only cares about
        # OnlineTrainer's hand-count threshold, not real back-to-back play.
        gc, agents, buffers = make_training_game(num_players=2)
        trainer = OnlineTrainer(hands_per_update=2)
        play_hand(gc, agents)

        trainer.process_completed_hand(gc, agents)
        trainer.process_completed_hand(gc, agents)

        assert all(len(b) == 0 for b in buffers)  # drained by the triggered update()

    def test_hands_per_update_is_coerced_to_at_least_one(self):
        trainer = OnlineTrainer(hands_per_update=0)
        assert trainer.hands_per_update == 1


class TestPolicyActuallyLearnsSomething:
    def test_repeated_hands_change_policy_parameters(self):
        gc, agents, _ = make_training_game(num_players=2, stack=5000, sb=1, bb=2)
        agent = agents[0]
        before = [p.clone() for p in agent.policy.parameters()]
        trainer = OnlineTrainer(hands_per_update=1)

        hands_played = 0
        for _ in range(3):
            # An untrained, possibly all-in-happy policy can bust a
            # heads-up opponent in one hand, after which start_hand() has
            # too few players with chips to deal to - stop before that.
            if any(p.stack <= 0 for p in gc.table.get_all_players()):
                break
            play_hand(gc, agents)
            trainer.process_completed_hand(gc, agents)
            hands_played += 1

        assert hands_played >= 1
        after = list(agent.policy.parameters())
        assert any(not torch.equal(b, a) for b, a in zip(before, after))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
