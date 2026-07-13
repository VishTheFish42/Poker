"""Difficulty modes and policy persistence for AI opponents (Task 5.5).

Maps each `poker.engine.player.Difficulty` tier to a sampling temperature
for `RLAgent`: novice explores more (a flatter, more random distribution
over actions, so it plays looser regardless of how good its underlying
weights are), advanced sticks close to its policy's top choice. This
keeps difficulty meaningful even before any real training has happened -
temperature alone separates the tiers, no per-tier weights required.

`build_agent()` also transparently restores a saved policy checkpoint for
that difficulty if one exists on disk (from a previous session's
training via `RLAgent.save()`), falling back to a fresh network
otherwise - specs/design.md's Training Strategy: "Save the policy state
after each session if feasible."
"""

from pathlib import Path
from typing import Optional, Union

from ..engine.player import Difficulty
from .replay_buffer import ReplayBuffer
from .rl_agent import RLAgent

DIFFICULTY_TEMPERATURES = {
    Difficulty.NOVICE: 2.0,
    Difficulty.INTERMEDIATE: 1.0,
    Difficulty.ADVANCED: 0.5,
}

DEFAULT_CHECKPOINT_NAMES = {
    Difficulty.NOVICE: "novice.pt",
    Difficulty.INTERMEDIATE: "intermediate.pt",
    Difficulty.ADVANCED: "advanced.pt",
}


def checkpoint_path(difficulty: Difficulty, checkpoint_dir: Union[str, Path]) -> Path:
    """The conventional checkpoint file path for `difficulty` within `checkpoint_dir`."""
    return Path(checkpoint_dir) / DEFAULT_CHECKPOINT_NAMES[difficulty]


def build_agent(
    difficulty: Difficulty,
    checkpoint_dir: Optional[Union[str, Path]] = None,
    replay_buffer: Optional[ReplayBuffer] = None,
) -> RLAgent:
    """Build an `RLAgent` configured for `difficulty`.

    Args:
        difficulty: Which tier to build for - controls the sampling
            temperature (how much the agent explores vs. exploits its
            current policy; see `DIFFICULTY_TEMPERATURES`).
        checkpoint_dir: Directory to look for a previously-saved policy
            checkpoint for this difficulty (see `checkpoint_path()`). If
            given and the file exists, the agent's network is restored
            from it; otherwise a fresh, randomly-initialized network is
            used - so this is always safe to call even before any
            training has ever been saved.
        replay_buffer: Attach one to make the returned agent trainable
            (see `RLAgent`).

    Returns:
        A configured `RLAgent`, ready to be handed to
        `AIPlayer.set_agent()`.
    """
    temperature = DIFFICULTY_TEMPERATURES[difficulty]
    path = checkpoint_path(difficulty, checkpoint_dir) if checkpoint_dir is not None else None

    if path is not None and path.exists():
        return RLAgent.load(path, temperature=temperature, replay_buffer=replay_buffer)

    return RLAgent(temperature=temperature, replay_buffer=replay_buffer)


def save_agent(agent: RLAgent, difficulty: Difficulty, checkpoint_dir: Union[str, Path]) -> Path:
    """Save `agent`'s policy under `difficulty`'s conventional checkpoint path.

    Args:
        agent: The agent whose policy network should be persisted.
        difficulty: Which tier this agent represents.
        checkpoint_dir: Directory `build_agent()` will later look in.

    Returns:
        The path the checkpoint was written to.
    """
    path = checkpoint_path(difficulty, checkpoint_dir)
    agent.save(path)
    return path
