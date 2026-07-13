"""Unit tests for the actor-critic policy network (Task 5.2)."""

import pytest
import torch

from src.poker.ai.action_space import ActionSpace
from src.poker.ai.observation import ObservationEncoder
from src.poker.ai.policy_network import PolicyNetwork


class TestDefaultShapes:
    def test_default_sizes_match_observation_and_action_spaces(self):
        network = PolicyNetwork()
        observation = torch.zeros((1, ObservationEncoder.size()))

        logits, value = network(observation)

        assert logits.shape == (1, ActionSpace.size())
        assert value.shape == (1,)

    def test_batched_forward_pass(self):
        network = PolicyNetwork()
        batch = torch.zeros((4, ObservationEncoder.size()))

        logits, value = network(batch)

        assert logits.shape == (4, ActionSpace.size())
        assert value.shape == (4,)


class TestCustomSizes:
    def test_custom_observation_and_action_size(self):
        network = PolicyNetwork(observation_size=10, action_size=3, hidden_sizes=(16,))
        observation = torch.zeros((2, 10))

        logits, value = network(observation)

        assert logits.shape == (2, 3)
        assert value.shape == (2,)

    def test_custom_hidden_sizes_still_produce_correct_output_shape(self):
        network = PolicyNetwork(hidden_sizes=(32, 16, 8))
        observation = torch.zeros((1, ObservationEncoder.size()))

        logits, value = network(observation)

        assert logits.shape == (1, ActionSpace.size())
        assert value.shape == (1,)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
