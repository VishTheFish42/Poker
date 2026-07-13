"""Unit and integration tests for OnlineTrainer (Task 5.4), using real
GameController/AIPlayer/RLAgent objects (not mocks) so hand outcomes,
rewards, and policy updates are all exercised end to end.
"""

import pytest
import torch

from src.poker.ai.action_space import AIAction
from src.poker.ai.online_trainer import OnlineTrainer
from src.poker.ai.replay_buffer import ReplayBuffer
from src.poker.ai.rl_agent import RLAgent
from src.poker.engine.controller import GameController
from src.poker.engine.player import AIPlayer, Player
from src.poker.engine.table import Table


def make_training_controller(num_players=3, stack=1000, sb=1, bb=2):
    """A table where every seat is an AIPlayer with a training-enabled RLAgent."""
    table = Table(num_players)
    buffers = []
    for seat in range(num_players):
        player = AIPlayer(f"AI{seat}", seat, stack)
        buffer = ReplayBuffer()
        player.set_agent(RLAgent(replay_buffer=buffer, deterministic=True))
        table.add_player(player)
        buffers.append(buffer)
    gc = GameController(table, sb, bb)
    return gc, buffers


def make_mixed_controller(stack=1000, sb=1, bb=2):
    """One training AI, one plain (inference-only) Player, for edge cases.

    A bare `Player` has no way to act via `auto_advance()` (it's neither a
    `HumanPlayer` nor an `AIPlayer`), so the hand would stall forever if
    action ever reached seat 1. The AI's decision is forced to FOLD so the
    heads-up hand resolves uncontested after seat 0's first turn, without
    seat 1 ever needing to act.
    """
    table = Table(2)
    ai_player = AIPlayer("AI", 0, stack)
    agent = RLAgent(replay_buffer=ReplayBuffer(), deterministic=True)
    original_choose = agent._choose
    agent._choose = lambda logits, mask: (AIAction.FOLD,) + original_choose(logits, mask)[1:]
    ai_player.set_agent(agent)
    table.add_player(ai_player)
    table.add_player(Player("Human", 1, stack))
    return GameController(table, sb, bb)


class TestProcessCompletedHand:
    def test_returns_empty_dict_when_no_result_yet(self):
        gc, _ = make_training_controller()
        trainer = OnlineTrainer()

        assert trainer.process_completed_hand(gc) == {}

    def test_returns_a_reward_for_every_seat_that_acted(self):
        gc, _ = make_training_controller(num_players=2)
        gc.start_new_hand()
        trainer = OnlineTrainer()

        rewards = trainer.process_completed_hand(gc)

        assert set(rewards.keys()) == {0, 1}
        assert all(isinstance(v, float) for v in rewards.values())

    def test_pushes_experiences_into_each_agents_buffer(self):
        gc, buffers = make_training_controller(num_players=2)
        gc.start_new_hand()
        trainer = OnlineTrainer(hands_per_update=1000)  # avoid auto-update clearing buffers

        trainer.process_completed_hand(gc)

        assert any(len(b) > 0 for b in buffers)

    def test_non_training_player_is_skipped(self):
        gc = make_mixed_controller()
        gc.start_new_hand()
        trainer = OnlineTrainer()

        rewards = trainer.process_completed_hand(gc)

        assert 1 not in rewards  # seat 1 is a plain Player, not an AIPlayer/RLAgent
        assert 0 in rewards


class TestPeriodicUpdate:
    def test_update_not_triggered_before_hands_per_update(self):
        gc, buffers = make_training_controller(num_players=2)
        gc.start_new_hand()
        trainer = OnlineTrainer(hands_per_update=2)

        trainer.process_completed_hand(gc)

        assert any(len(b) > 0 for b in buffers)  # still sitting there, unconsumed

    def test_update_triggered_after_hands_per_update(self):
        # Deliberately processes the same completed hand twice rather than
        # dealing a second one: a heads-up deterministic policy can bust a
        # player in a single hand, which would leave too few active seats
        # for start_new_hand() to deal to - see the busted-stack guard used
        # in test_rl_agent.py's multi-hand tests. This test only cares about
        # OnlineTrainer's hand-count threshold, not real back-to-back play.
        gc, buffers = make_training_controller(num_players=2)
        trainer = OnlineTrainer(hands_per_update=2)
        gc.start_new_hand()

        trainer.process_completed_hand(gc)
        trainer.process_completed_hand(gc)

        assert all(len(b) == 0 for b in buffers)  # drained by the triggered update()

    def test_hands_per_update_is_coerced_to_at_least_one(self):
        trainer = OnlineTrainer(hands_per_update=0)
        assert trainer.hands_per_update == 1


class TestPolicyActuallyLearnsSomething:
    def test_repeated_hands_change_policy_parameters(self):
        gc, buffers = make_training_controller(num_players=2, stack=5000, sb=1, bb=2)
        agent = gc.table.get_player(0).ai_agent
        before = [p.clone() for p in agent.policy.parameters()]
        trainer = OnlineTrainer(hands_per_update=1)

        hands_played = 0
        for _ in range(3):
            # An untrained, possibly all-in-happy policy can bust a
            # heads-up opponent in one hand, after which start_new_hand()
            # has too few active seats to deal to - stop before that.
            if any(p.stack <= 0 for p in gc.table.get_all_players()):
                break
            gc.start_new_hand()
            trainer.process_completed_hand(gc)
            hands_played += 1

        assert hands_played >= 1
        after = list(agent.policy.parameters())
        assert any(not torch.equal(b, a) for b, a in zip(before, after))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
