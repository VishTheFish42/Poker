"""Unit tests for the experience replay buffer (Task 5.4)."""

import torch
import pytest

from src.poker.ai.replay_buffer import Experience, ReplayBuffer


def make_experience(reward=1.0):
    zero = torch.tensor(0.0)
    return Experience(log_prob=zero, value=zero, entropy=zero, reward=reward)


class TestAddAndDrain:
    def test_starts_empty(self):
        buffer = ReplayBuffer()
        assert len(buffer) == 0

    def test_add_increases_length(self):
        buffer = ReplayBuffer()
        buffer.add(make_experience())
        assert len(buffer) == 1

    def test_drain_returns_all_and_clears(self):
        buffer = ReplayBuffer()
        buffer.add(make_experience(1.0))
        buffer.add(make_experience(2.0))

        experiences = buffer.drain()

        assert [e.reward for e in experiences] == [1.0, 2.0]
        assert len(buffer) == 0

    def test_drain_on_empty_buffer_returns_empty_list(self):
        buffer = ReplayBuffer()
        assert buffer.drain() == []


class TestCapacity:
    def test_unbounded_by_default(self):
        buffer = ReplayBuffer()
        for i in range(100):
            buffer.add(make_experience(float(i)))
        assert len(buffer) == 100

    def test_evicts_oldest_when_over_capacity(self):
        buffer = ReplayBuffer(capacity=3)
        for i in range(5):
            buffer.add(make_experience(float(i)))

        experiences = buffer.drain()

        assert len(experiences) == 3
        assert [e.reward for e in experiences] == [2.0, 3.0, 4.0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
