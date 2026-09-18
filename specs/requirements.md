# Poker Game Requirements

## Project Overview
Build a fully functional Texas Hold'em poker game with a rules engine written in C++, intelligent opponents powered by a Python-based reinforcement learning layer, and a desktop frontend to be designed in a later phase.

## Primary Goals
- Implement a complete Texas Hold'em game engine with all official rules, in C++, with an object-oriented design.
- Expose that engine to Python through explicit bindings, so the AI layer (and, later, the frontend if it's Python-based) can drive it without re-implementing any rules.
- Include AI opponents that learn via an RL-based approach during play.
- Make the system modular and independently testable at each layer (engine / bindings / AI / frontend).
- Defer the frontend build until the engine and AI layers are stable; it will be designed against their real, finished API rather than guessed at up front.

## Functional Requirements

### Game Setup
- Allow a human player to be seated with a chosen name and buy-in.
- Support a configurable number of total seats, up to 10.
- Support configurable small and big blinds.
- Initialize a table with one dealer button, blinds, and seating.

### Gameplay Rules
- Play standard Texas Hold'em with:
  - Two private hole cards per player.
  - Pre-flop, flop, turn, and river betting rounds.
  - Dealer button rotation and blind posting.
  - Check, call, bet, raise, and fold actions, plus all-in.
- Implement all hand ranking rules:
  - High card, pair, two pair, three of a kind, straight, flush, full house, four of a kind, straight flush, royal flush.
- Resolve ties and split pots correctly.
- Handle side pots for all-in players.
- Automatically advance the game after each action and round, with an explicit step-by-step mode available so a caller (AI loop, future UI, tests) can pace turns one at a time.

### Engine / Bindings Boundary
- The C++ engine owns all rules enforcement: legal-action checks, betting math, hand evaluation, pot distribution. It has no knowledge of who or what is deciding an action (human input, an RL policy, a script) — it only validates and applies whatever action it's given.
- A pybind11 module exposes the engine's public classes, enums, and the game controller's action/query methods to Python, with the same semantics as the native C++ API (no logic duplicated in the binding layer).
- Anything that decides *which* action to take for a given seat (human input handling, AI inference) lives outside the engine, on the caller's side of the binding.

### AI Opponents
- Create AI opponents using reinforcement learning, implemented in Python (PyTorch), driving the engine through the pybind11 bindings.
- AI should observe game state (via the bindings) and choose actions each betting round.
- Use an RL training process that can run while a game is in progress.
- Maintain per-player learning state so AI agents improve over time.
- Provide at least two difficulty tiers: novice and advanced.

### Frontend (Deferred)
- No frontend toolkit or language is committed to yet.
- A future spec revision will choose the frontend approach once the engine and AI layers are stable, and will define its own requirements against the engine's public API (via bindings or otherwise).

### Persistence and Configuration
- Save AI agent policy state between runs.
- Game/session configuration persistence is out of scope until the frontend is designed.

## Non-Functional Requirements
- Engine: C++20, object-oriented, built with CMake, unit-tested with GoogleTest.
- AI: Python 3.11+, PyTorch, unit-tested with pytest.
- Bindings: pybind11, built as an optional CMake target so the engine can be built and tested standalone without a Python toolchain present.
- Clean separation of concerns: the engine must never depend on Python, AI concepts, or any frontend; the AI layer must never re-implement rules the engine already enforces.
- Provide documentation for the module design, updated as each layer's real API stabilizes.

## Constraints
- Desktop-only application for macOS/Windows/Linux (engine and bindings are portable C++/Python; no platform-specific rules logic).
- No network multiplayer required in the initial version.
- The AI should be explainable and not require huge training datasets.
- Keep the game self-contained and runnable locally.

## Acceptance Criteria
- The C++ engine runs through all Texas Hold'em stages correctly, verified by GoogleTest coverage of card/deck, hand evaluation, betting, pot resolution (including side pots), and showdown.
- The pybind11 bindings expose enough of the engine for a pure-Python driver script to play a full hand end to end with no frontend.
- AI opponents make decisions using an RL-based model, driven entirely through the bindings, and demonstrate learning behavior over multiple hands.
- Each layer (engine, bindings, AI) has its own test suite and can be built/tested independently.
