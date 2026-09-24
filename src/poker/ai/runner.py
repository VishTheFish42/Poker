"""Drives engine hands for AI-controlled seats.

The C++ engine never decides who acts or how - it only validates and
applies actions (specs/design.md). This module is the Python-side
orchestration that does: given a `GameController` and a `{seat: RLAgent}`
mapping, it asks each AI seat's agent for an action when that seat is on
the clock, and runs any pending engine steps (dealing the next street, an
all-in runout, the showdown) in between.

A seat with no agent (e.g. a human) stops the loop so the caller can
supply that seat's action via `GameController.submit_action()` and then
resume.
"""

from typing import Mapping, Optional, Sequence

from poker_engine import Card, GameController, HandPhase, ShowdownResult

from .rl_agent import RLAgent


def run_ai_turns(controller: GameController, agents: Mapping[int, RLAgent]) -> Optional[int]:
    """Play AI seats' turns until the hand completes or a seat without an
    agent is on the clock.

    Pending engine steps (`HandPhase.PENDING_ADVANCE`, which only occur in
    `ProgressionMode.SINGLE_STEP`) are run as they come up.

    Args:
        controller: A controller with a hand in progress (or complete).
        agents: `{seat: agent}` for the AI seats.

    Returns:
        The seat waiting for a non-AI action, or None once the hand is
        complete.
    """
    while True:
        phase = controller.phase
        if phase == HandPhase.PENDING_ADVANCE:
            controller.step_once()
        elif phase == HandPhase.AWAITING_ACTION:
            seat = controller.current_seat
            agent = agents.get(seat)
            if agent is None:
                return seat
            controller.submit_action(agent.select_action(controller, seat))
        else:
            return None


def play_hand(
    controller: GameController,
    agents: Mapping[int, RLAgent],
    stacked_cards: Sequence[Card] = (),
) -> ShowdownResult:
    """Start a hand and play it to completion with every seat AI-controlled.

    Args:
        controller: The controller to deal the hand on.
        agents: `{seat: agent}` covering every seat that will be dealt in.
        stacked_cards: Forwarded to `GameController.start_hand()`, for
            scripted deals.

    Returns:
        The hand's `ShowdownResult` (also on `controller.last_result`).

    Raises:
        RuntimeError: If the hand can't start (see
            `GameController.start_hand()` - e.g. fewer than 2 players
            have chips left, i.e. the match is over).
        ValueError: If a seat without an agent comes on the clock; the
            hand is left in progress at that point.
    """
    controller.start_hand(list(stacked_cards))
    waiting_seat = run_ai_turns(controller, agents)
    if waiting_seat is not None:
        raise ValueError(f"seat {waiting_seat} is on the clock but has no agent")
    return controller.last_result
