"""Unit and integration tests for RLAgent (Task 5.2), using a real
GameController/AIPlayer (not mocks) so every produced action is checked
against the engine's own legality rules.
"""

import pytest
import torch

from src.poker.ai.action_space import AIAction
from src.poker.ai.replay_buffer import ReplayBuffer
from src.poker.ai.rl_agent import RLAgent
from src.poker.engine.card import Card, CardRank as R, CardSuit as S
from src.poker.engine.controller import GameController
from src.poker.engine.player import AIPlayer, Player
from src.poker.engine.table import Table


def make_controller(num_players=3, stack=1000, sb=1, bb=2):
    table = Table(num_players)
    for seat in range(num_players):
        table.add_player(Player(f"P{seat}", seat, stack))
    gc = GameController(table, sb, bb)
    gc.start_new_hand()
    return gc


def make_ai_controller(num_players=3, stack=1000, sb=1, bb=2, agent_factory=None):
    agent_factory = agent_factory or (lambda: RLAgent(deterministic=True))
    table = Table(num_players)
    for seat in range(num_players):
        player = AIPlayer(f"AI{seat}", seat, stack)
        player.set_agent(agent_factory())
        table.add_player(player)
    return GameController(table, sb, bb)


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
        player = gc.get_current_player()
        agent = RLAgent()

        for _ in range(20):
            action = agent.select_action(gc._build_game_state_view(), player)
            assert gc.validate_action(action) is None

    def test_masking_respected_when_only_passive_actions_are_legal(self):
        gc = make_controller(num_players=2, stack=1000, sb=1, bb=2)
        gc.go_all_in()  # seat 0 shoves; seat 1 can only fold/call-all-in, never bet/raise
        player = gc.get_current_player()
        agent = RLAgent()

        for _ in range(20):
            action = agent.select_action(gc._build_game_state_view(), player)
            assert gc.validate_action(action) is None
            assert action.action_type.value not in ("bet", "raise")

    def test_legal_action_on_the_flop_with_no_bet_yet(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        gc.check_or_call()
        gc.check_or_call()  # flop, no bet yet
        player = gc.get_current_player()
        agent = RLAgent()

        action = agent.select_action(gc._build_game_state_view(), player)
        assert gc.validate_action(action) is None


class TestDeterministicMode:
    def test_same_state_yields_the_same_action_repeatedly(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        player = gc.get_current_player()
        agent = RLAgent(deterministic=True)
        game_state = gc._build_game_state_view()

        first = agent.select_action(game_state, player)
        second = agent.select_action(game_state, player)

        assert first.action_type == second.action_type
        assert first.amount == second.amount


class TestFullHandIntegration:
    def test_all_ai_hand_plays_to_completion(self):
        gc = make_ai_controller(num_players=3, sb=1, bb=2)
        gc.start_new_hand()  # auto_advance() runs the whole hand: every seat has an agent
        assert gc.is_hand_complete

    def test_no_exceptions_across_several_hands(self):
        gc = make_ai_controller(
            num_players=3, stack=200, sb=5, bb=10, agent_factory=lambda: RLAgent(temperature=1.5)
        )
        for _ in range(5):
            if any(p.stack <= 0 for p in gc.table.get_all_players()):
                break
            gc.start_new_hand()  # start_new_hand() rotates the button itself
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
        player = gc.get_current_player()
        buffer = ReplayBuffer()
        agent = RLAgent(replay_buffer=buffer)

        agent.select_action(gc._build_game_state_view(), player)

        assert len(agent._pending) == 1
        assert len(buffer) == 0  # not pushed into the buffer until finish_hand()

    def test_no_recording_when_not_training(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        player = gc.get_current_player()
        agent = RLAgent()

        agent.select_action(gc._build_game_state_view(), player)

        assert agent._pending == []


class TestFinishHand:
    def test_pushes_one_experience_per_pending_action(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        player = gc.get_current_player()
        buffer = ReplayBuffer()
        agent = RLAgent(replay_buffer=buffer)
        agent.select_action(gc._build_game_state_view(), player)
        agent.select_action(gc._build_game_state_view(), player)

        agent.finish_hand(base_reward=1.5)

        assert len(buffer) == 2
        assert agent._pending == []

    def test_experience_reward_matches_base_reward_for_non_fold_action(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        gc.check_or_call()
        gc.check_or_call()  # flop, no bet yet
        player = gc.get_current_player()
        buffer = ReplayBuffer()
        agent = RLAgent(replay_buffer=buffer)
        # Force a non-FOLD decision so the reward can't include any
        # fold-strength shaping, regardless of what the untrained network prefers.
        original_choose = agent._choose
        agent._choose = lambda logits, mask: (
            (AIAction.CHECK_CALL,) + original_choose(logits, mask)[1:]
        )

        agent.select_action(gc._build_game_state_view(), player)
        agent.finish_hand(base_reward=2.0)
        experiences = buffer.drain()

        assert experiences[0].reward == pytest.approx(2.0)

    def test_fold_strength_penalty_is_added_for_a_folded_strong_hand(self):
        gc = make_controller(num_players=2, stack=1000, sb=1, bb=2)
        gc.check_or_call()
        gc.check_or_call()  # reach the flop
        gc.table.community_cards = [Card(S.HEARTS, R.QUEEN), Card(S.DIAMONDS, R.QUEEN), Card(S.CLUBS, R.TWO)]
        player = gc.get_current_player()
        player.hole_cards = [Card(S.CLUBS, R.KING), Card(S.SPADES, R.KING)]  # two pair with the board

        buffer = ReplayBuffer()
        agent = RLAgent(replay_buffer=buffer)
        # Force a FOLD decision to exercise the fold-strength path deterministically.
        original_choose = agent._choose
        agent._choose = lambda logits, mask: (AIAction.FOLD,) + original_choose(logits, mask)[1:]

        agent.select_action(gc._build_game_state_view(), player)
        agent.finish_hand(base_reward=-0.2)
        experiences = buffer.drain()

        assert experiences[0].reward < -0.2  # base reward plus a negative strength penalty

    def test_noop_when_not_training(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        player = gc.get_current_player()
        agent = RLAgent()

        agent.finish_hand(base_reward=1.0)  # should not raise

        assert agent._pending == []


class TestUpdate:
    def test_returns_none_for_empty_buffer(self):
        agent = RLAgent(replay_buffer=ReplayBuffer())
        assert agent.update() is None

    def test_update_changes_policy_parameters(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        player = gc.get_current_player()
        buffer = ReplayBuffer()
        agent = RLAgent(replay_buffer=buffer)

        before = [p.clone() for p in agent.policy.parameters()]
        for _ in range(4):
            agent.select_action(gc._build_game_state_view(), player)
        agent.finish_hand(base_reward=3.0)
        loss = agent.update()
        after = list(agent.policy.parameters())

        assert loss is not None
        assert any(not torch.equal(b, a) for b, a in zip(before, after))

    def test_update_clears_the_buffer(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        player = gc.get_current_player()
        buffer = ReplayBuffer()
        agent = RLAgent(replay_buffer=buffer)
        agent.select_action(gc._build_game_state_view(), player)
        agent.finish_hand(base_reward=1.0)

        agent.update()

        assert len(buffer) == 0

    def test_policy_returns_to_eval_mode_after_update(self):
        gc = make_controller(num_players=2, sb=1, bb=2)
        player = gc.get_current_player()
        buffer = ReplayBuffer()
        agent = RLAgent(replay_buffer=buffer)
        agent.select_action(gc._build_game_state_view(), player)
        agent.finish_hand(base_reward=1.0)

        agent.update()

        assert not agent.policy.training


class TestFullHandIntegrationWithTraining:
    def test_all_ai_training_hand_completes_and_can_be_finished(self):
        buffers = [ReplayBuffer() for _ in range(3)]
        gc = make_ai_controller(
            num_players=3,
            sb=1,
            bb=2,
            agent_factory=iter([RLAgent(replay_buffer=b, deterministic=True) for b in buffers]).__next__,
        )
        gc.start_new_hand()
        assert gc.is_hand_complete

        for player, buffer in zip(gc.table.get_all_players(), buffers):
            player.ai_agent.finish_hand(base_reward=0.0)
            player.ai_agent.update()  # should not raise even with 0 or few experiences


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
        player = gc.get_current_player()
        buffer = ReplayBuffer()
        agent = RLAgent(replay_buffer=buffer)
        for _ in range(3):
            agent.select_action(gc._build_game_state_view(), player)
        agent.finish_hand(base_reward=1.0)
        agent.update()  # actually changes the weights from their random init

        checkpoint = tmp_path / "policy.pt"
        agent.save(checkpoint)
        loaded = RLAgent.load(checkpoint)

        for original, restored in zip(agent.policy.parameters(), loaded.policy.parameters()):
            assert torch.equal(original, restored)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
