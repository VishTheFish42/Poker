"""Integration tests simulating full AI-driven training matches (Task 5.6).

Where the other Phase 5 test files check one module's behavior in
isolation, these run many simulated hands end to end - the real C++
engine plus real RLAgent/OnlineTrainer objects, no mocks - to catch the
kind of bug that only shows up over an extended run: chip accounting
drift, exploding/NaN policy weights, a training loop that eventually
crashes, or difficulty tiers that don't actually behave differently once
temperature is the only thing separating them.

Each test seeds torch and the deck so a failure reproduces exactly.
"""

import pytest
import torch

from src.poker.ai.action_space import ActionSpace
from src.poker.ai.difficulty import DIFFICULTY_TEMPERATURES, Difficulty, build_agent
from src.poker.ai.observation import ObservationEncoder
from src.poker.ai.online_trainer import OnlineTrainer
from src.poker.ai.policy_network import PolicyNetwork
from src.poker.ai.replay_buffer import ReplayBuffer
from src.poker.ai.rl_agent import RLAgent
from src.poker.ai.runner import play_hand
from tests.engine_helpers import make_controller


@pytest.fixture(autouse=True)
def seeded():
    torch.manual_seed(0)


def make_training_game(num_players=4, stack=1000, sb=5, bb=10, temperature=1.0):
    """A controller (no hand started) with a training-enabled RLAgent per seat."""
    gc = make_controller(num_players=num_players, stack=stack, sb=sb, bb=bb, start=False)
    gc.table.deck.seed(0)
    agents = {
        seat: RLAgent(replay_buffer=ReplayBuffer(), temperature=temperature) for seat in range(num_players)
    }
    return gc, agents


def players_with_chips(gc):
    return sum(p.has_chips for p in gc.table.get_all_players())


class TestChipConservation:
    """A poker table never creates or destroys chips - only moves them
    between players. Running many AI-driven hands is a good fuzz test of
    that invariant across the whole engine (betting, pot/side-pot math,
    showdown payouts) as seen through the bindings, not just the AI layer.
    """

    def test_total_chips_conserved_across_a_simulated_match(self):
        num_players, stack = 4, 1000
        gc, agents = make_training_game(num_players=num_players, stack=stack, sb=5, bb=10)
        trainer = OnlineTrainer(hands_per_update=3)

        hands_played = 0
        for _ in range(30):
            if players_with_chips(gc) < 2:
                break
            play_hand(gc, agents)
            trainer.process_completed_hand(gc, agents)
            hands_played += 1
            assert sum(p.stack for p in gc.table.get_all_players()) == num_players * stack

        assert hands_played > 0


class TestTrainingStabilityOverASimulatedMatch:
    def test_no_exceptions_across_many_hands(self):
        # hands_played isn't asserted to reach any particular count: an
        # untrained (randomly-initialized) policy can plausibly go all-in
        # and bust an opponent within the first hand or two, which is a
        # legitimate match outcome, not a bug. What this test actually
        # checks is that reaching that point - or playing the full 25
        # hands - never raises; >= 1 just guards against the loop body
        # vacuously never running at all.
        gc, agents = make_training_game(num_players=3, stack=3000, sb=5, bb=10)
        trainer = OnlineTrainer(hands_per_update=2)

        hands_played = 0
        for _ in range(25):
            if players_with_chips(gc) < 2:
                break
            play_hand(gc, agents)
            trainer.process_completed_hand(gc, agents)
            hands_played += 1

        assert hands_played >= 1

    def test_policy_parameters_stay_finite(self):
        gc, agents = make_training_game(num_players=3, stack=3000, sb=5, bb=10)
        trainer = OnlineTrainer(hands_per_update=1)

        for _ in range(20):
            if players_with_chips(gc) < 2:
                break
            play_hand(gc, agents)
            trainer.process_completed_hand(gc, agents)

        for agent in agents.values():
            for param in agent.policy.parameters():
                assert torch.isfinite(param).all()

    def test_running_out_of_players_ends_the_match_cleanly(self):
        # Short stacks relative to the blinds, so the match reliably ends
        # within the hand limit - this confirms it ends via a catchable
        # RuntimeError from GameController.start_hand() (fewer than 2
        # players with chips) rather than a crash. Simulating a whole
        # match includes it actually ending.
        gc, agents = make_training_game(num_players=2, stack=40, sb=5, bb=10)
        trainer = OnlineTrainer()

        game_over = False
        for _ in range(200):
            try:
                play_hand(gc, agents)
            except RuntimeError:
                game_over = True
                break
            trainer.process_completed_hand(gc, agents)

        assert game_over
        assert players_with_chips(gc) == 1


class TestDifficultyProducesDifferentBehavior:
    """Task 5.5 gives each difficulty tier its own sampling temperature;
    these confirm that actually changes the AI's behavior, not just an
    attribute nobody reads.
    """

    def test_novice_distribution_has_higher_entropy_than_advanced(self):
        # Load identical weights into both networks so temperature is the
        # only variable - isolates whether difficulty changes behavior, as
        # opposed to two random networks merely happening to differ.
        shared_state = PolicyNetwork().state_dict()
        novice_policy = PolicyNetwork()
        novice_policy.load_state_dict(shared_state)
        advanced_policy = PolicyNetwork()
        advanced_policy.load_state_dict(shared_state)

        novice_agent = RLAgent(policy=novice_policy, temperature=DIFFICULTY_TEMPERATURES[Difficulty.NOVICE])
        advanced_agent = RLAgent(
            policy=advanced_policy, temperature=DIFFICULTY_TEMPERATURES[Difficulty.ADVANCED]
        )

        gc = make_controller(num_players=2, sb=5, bb=10)
        observation = ObservationEncoder.encode(gc, gc.current_seat)
        observation_tensor = torch.tensor(observation.tolist(), dtype=torch.float32).unsqueeze(0)
        mask = ActionSpace.legal_mask(gc.legal_actions())

        with torch.no_grad():
            novice_logits, _ = novice_policy(observation_tensor)
            advanced_logits, _ = advanced_policy(observation_tensor)

        _, _, novice_entropy = novice_agent._choose(novice_logits.squeeze(0), mask)
        _, _, advanced_entropy = advanced_agent._choose(advanced_logits.squeeze(0), mask)

        assert novice_entropy.item() > advanced_entropy.item()

    def test_build_agent_wires_up_the_expected_temperature_per_tier(self):
        for difficulty in Difficulty:
            agent = build_agent(difficulty)
            assert agent.temperature == DIFFICULTY_TEMPERATURES[difficulty]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
