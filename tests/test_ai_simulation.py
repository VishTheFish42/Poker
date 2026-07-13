"""Integration tests simulating full AI-driven training matches (Task 5.6).

Where the other Phase 5 test files check one module's behavior in
isolation, these run many simulated hands end to end - real
Table/GameController/AIPlayer/RLAgent/OnlineTrainer objects, no mocks -
to catch the kind of bug that only shows up over an extended run: chip
accounting drift, exploding/NaN policy weights, a training loop that
eventually crashes, or difficulty tiers that don't actually behave
differently once temperature is the only thing separating them.
"""

import pytest
import torch

from src.poker.ai.action_space import ActionSpace
from src.poker.ai.difficulty import DIFFICULTY_TEMPERATURES, build_agent
from src.poker.ai.observation import ObservationEncoder
from src.poker.ai.online_trainer import OnlineTrainer
from src.poker.ai.policy_network import PolicyNetwork
from src.poker.ai.replay_buffer import ReplayBuffer
from src.poker.ai.rl_agent import RLAgent
from src.poker.engine.controller import GameController
from src.poker.engine.player import AIPlayer, Difficulty, Player
from src.poker.engine.table import Table


def make_training_table(num_players=4, stack=1000, sb=5, bb=10, temperature=1.0):
    """A table where every seat is an AIPlayer with a training-enabled RLAgent."""
    table = Table(num_players)
    buffers = []
    for seat in range(num_players):
        player = AIPlayer(f"AI{seat}", seat, stack)
        buffer = ReplayBuffer()
        player.set_agent(RLAgent(replay_buffer=buffer, temperature=temperature))
        table.add_player(player)
        buffers.append(buffer)
    return GameController(table, sb, bb), buffers


class TestChipConservation:
    """A poker table never creates or destroys chips - only moves them
    between players. Running many AI-driven hands is a good fuzz test of
    that invariant across the whole engine (betting, pot/side-pot math,
    showdown payouts), not just the AI layer.
    """

    def test_total_chips_conserved_across_a_simulated_match(self):
        num_players, stack = 4, 1000
        gc, _ = make_training_table(num_players=num_players, stack=stack, sb=5, bb=10)
        total_chips = num_players * stack
        trainer = OnlineTrainer(hands_per_update=3)

        hands_played = 0
        for _ in range(30):
            if sum(1 for p in gc.table.get_all_players() if p.stack > 0) < 2:
                break
            gc.start_new_hand()
            trainer.process_completed_hand(gc)
            hands_played += 1
            assert sum(p.stack for p in gc.table.get_all_players()) == total_chips

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
        gc, _ = make_training_table(num_players=3, stack=3000, sb=5, bb=10)
        trainer = OnlineTrainer(hands_per_update=2)

        hands_played = 0
        for _ in range(25):
            if any(p.stack <= 0 for p in gc.table.get_all_players()):
                break
            gc.start_new_hand()
            trainer.process_completed_hand(gc)
            hands_played += 1

        assert hands_played >= 1

    def test_policy_parameters_stay_finite(self):
        gc, _ = make_training_table(num_players=3, stack=3000, sb=5, bb=10)
        trainer = OnlineTrainer(hands_per_update=1)

        for _ in range(20):
            if any(p.stack <= 0 for p in gc.table.get_all_players()):
                break
            gc.start_new_hand()
            trainer.process_completed_hand(gc)

        for player in gc.table.get_all_players():
            for param in player.ai_agent.policy.parameters():
                assert torch.isfinite(param).all()

    def test_running_out_of_players_ends_the_match_cleanly(self):
        # Short stacks relative to the blinds so forced blind posting alone
        # reliably busts a heads-up player within a handful of hands - this
        # confirms that ends the match via a catchable RuntimeError (see
        # GameController.start_new_hand's busted-player guard) rather than
        # a crash. Simulating a whole match includes it actually ending.
        gc, _ = make_training_table(num_players=2, stack=40, sb=5, bb=10)
        trainer = OnlineTrainer()

        game_over = False
        for _ in range(50):
            try:
                gc.start_new_hand()
            except RuntimeError:
                game_over = True
                break
            trainer.process_completed_hand(gc)

        assert game_over


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

        table = Table(2)
        table.add_player(Player("A", 0, 1000))
        table.add_player(Player("B", 1, 1000))
        gc = GameController(table, 5, 10)
        gc.start_new_hand()
        player = gc.get_current_player()
        game_state = gc._build_game_state_view()

        observation = ObservationEncoder.encode(gc, player.seat)
        observation_tensor = torch.tensor(observation.tolist(), dtype=torch.float32).unsqueeze(0)
        mask = ActionSpace.legal_mask(game_state["legal_actions"])

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
