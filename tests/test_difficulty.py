"""Unit tests for difficulty modes and policy persistence (Task 5.5)."""

import torch
import pytest

from src.poker.ai.difficulty import (
    DIFFICULTY_TEMPERATURES,
    build_agent,
    checkpoint_path,
    save_agent,
)
from src.poker.ai.replay_buffer import ReplayBuffer
from src.poker.ai.rl_agent import RLAgent
from src.poker.engine.player import Difficulty


class TestCheckpointPath:
    def test_each_difficulty_has_a_distinct_filename(self, tmp_path):
        paths = {checkpoint_path(d, tmp_path) for d in Difficulty}
        assert len(paths) == len(list(Difficulty))

    def test_path_is_under_the_given_directory(self, tmp_path):
        path = checkpoint_path(Difficulty.NOVICE, tmp_path)
        assert path.parent == tmp_path


class TestBuildAgentTemperature:
    @pytest.mark.parametrize("difficulty", list(Difficulty))
    def test_temperature_matches_difficulty_table(self, difficulty):
        agent = build_agent(difficulty)
        assert agent.temperature == DIFFICULTY_TEMPERATURES[difficulty]

    def test_novice_explores_more_than_advanced(self):
        assert DIFFICULTY_TEMPERATURES[Difficulty.NOVICE] > DIFFICULTY_TEMPERATURES[Difficulty.ADVANCED]

    def test_no_checkpoint_dir_gives_a_fresh_network(self):
        agent = build_agent(Difficulty.INTERMEDIATE)
        assert isinstance(agent, RLAgent)

    def test_missing_checkpoint_file_falls_back_to_fresh_network(self, tmp_path):
        agent = build_agent(Difficulty.ADVANCED, checkpoint_dir=tmp_path)
        assert isinstance(agent, RLAgent)


class TestBuildAgentAttachesReplayBuffer:
    def test_replay_buffer_forwarded_when_no_checkpoint(self):
        buffer = ReplayBuffer()
        agent = build_agent(Difficulty.NOVICE, replay_buffer=buffer)
        assert agent.replay_buffer is buffer

    def test_replay_buffer_forwarded_when_loading_a_checkpoint(self, tmp_path):
        save_agent(RLAgent(), Difficulty.NOVICE, tmp_path)
        buffer = ReplayBuffer()

        agent = build_agent(Difficulty.NOVICE, checkpoint_dir=tmp_path, replay_buffer=buffer)

        assert agent.replay_buffer is buffer


class TestSaveAndBuildRoundTrip:
    def test_saved_agent_is_restored_on_next_build(self, tmp_path):
        original = RLAgent()
        save_agent(original, Difficulty.ADVANCED, tmp_path)

        restored = build_agent(Difficulty.ADVANCED, checkpoint_dir=tmp_path)

        for original_param, restored_param in zip(original.policy.parameters(), restored.policy.parameters()):
            assert torch.equal(original_param, restored_param)

    def test_different_difficulties_do_not_collide(self, tmp_path):
        novice_agent = RLAgent()
        advanced_agent = RLAgent()
        save_agent(novice_agent, Difficulty.NOVICE, tmp_path)
        save_agent(advanced_agent, Difficulty.ADVANCED, tmp_path)

        restored_novice = build_agent(Difficulty.NOVICE, checkpoint_dir=tmp_path)
        restored_advanced = build_agent(Difficulty.ADVANCED, checkpoint_dir=tmp_path)

        novice_params = list(restored_novice.policy.parameters())
        advanced_params = list(restored_advanced.policy.parameters())
        assert any(
            not torch.equal(a, b) for a, b in zip(novice_params, advanced_params)
        )

    def test_save_agent_returns_the_checkpoint_path(self, tmp_path):
        path = save_agent(RLAgent(), Difficulty.INTERMEDIATE, tmp_path)
        assert path == checkpoint_path(Difficulty.INTERMEDIATE, tmp_path)
        assert path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
