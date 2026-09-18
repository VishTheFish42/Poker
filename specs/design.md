# Poker Game Design

## High-Level Architecture
The application is now split across four subsystems instead of three, with a hard language boundary between the first and the rest:

1. **Engine** (C++) — all poker rules. No Python, no AI, no UI concepts.
2. **Bindings** (pybind11) — a thin, logic-free translation of the engine's public API into a Python module.
3. **AI** (Python / PyTorch) — RL agents that observe engine state through the bindings and choose actions.
4. **Frontend** (deferred) — not designed yet. Whatever it ends up being, it talks to the engine only through the same public API the bindings expose (or a native C++ API directly, if the frontend also ends up being C++) — never by reaching into engine internals.

This is not quite MVC anymore: there is no single "Controller" shared across languages. The engine's `GameController` is the controller for *rules* (turn order, legal actions, round advancement). Anything that decides what action a seat takes — a human's click, an RL policy's inference — is orchestration logic that lives entirely on the Python (or future frontend) side and calls into the engine as a library.

## Module Overview

### `engine/` (C++)
- `Card` / `Suit` / `Rank`: suit and rank value types. (Implemented — see `engine/include/poker/card.hpp`.)
- `Deck`: generates, shuffles, and deals a 52-card deck. (Implemented — see `engine/include/poker/deck.hpp`.)
- `HandEvaluator`: computes Texas Hold'em hand strength and rank ordering from seven cards. (Implemented — see `engine/include/poker/hand_evaluator.hpp`.)
- `Player`: seat ownership, stack size, hole cards, and status (active / folded / all-in / out). A single concrete class — there is no `HumanPlayer`/`AIPlayer` split in the engine, because the engine doesn't care who's deciding; that distinction exists only in the Python orchestration layer. (Implemented — see `engine/include/poker/player.hpp`.)
- `Table`: holds players, dealer position, blinds, community cards, and pot state. (Implemented — see `engine/include/poker/table.hpp`.)
- `BettingRound`: manages action order, permissible actions, and current bets for one street. (Implemented — see `engine/include/poker/betting_round.hpp`.)
- `PotManager`: tracks the main pot and side pots. (Implemented — see `engine/include/poker/pot_manager.hpp`.)
- `Showdown`: resolves hand comparisons and pot distribution, including ties and split pots. (Implemented — see `engine/include/poker/showdown.hpp`.)
- `GameController`: orchestrates a hand — dealing, blind posting, round transitions, showdown — and exposes both a fully-automatic `advance()` and a single-step `stepOnce()`, since a caller (an AI loop, tests, a future frontend) needs to pace turns one at a time rather than jump straight to the final state. (Not yet implemented — Phase 3.)

Each class lives as a `<name>.hpp` / `<name>.cpp` pair under `engine/include/poker/` and `engine/src/`, with a matching `engine/tests/test_<name>.cpp`.

### `bindings/` (pybind11)
- One module (name TBD when built) that wraps every `engine/` class and enum needed by the AI layer: `Card`, `Deck`, `Player`, `Table`, `GameController`, the action/result types, and any query methods the observation encoder needs (legal actions, pot size, stacks, stage, etc.).
- No rules logic here — if something needs a rules decision, it belongs in `engine/`, not in a binding wrapper function.
- Built only when `POKER_BUILD_PYTHON_BINDINGS=ON` is passed to CMake, so the engine and its GoogleTest suite build standalone without a Python dev environment.

### `ai/` (Python, under `src/poker/ai/`)
- `RLAgent`: encapsulates the policy network and training loop.
- `PolicyNetwork`: neural model mapping observations to action probabilities (PyTorch).
- `ReplayBuffer`: stores experience tuples for policy updates.
- `ActionSpace`: defines fold, call/check, and raise/bet choices.
- `ObservationEncoder`: converts engine state (read through the bindings) into numeric features.
- `RewardCalculator`: computes reward signals from hand outcomes.
- `OnlineTrainer`: runs policy updates between hands during live play.
- `difficulty`: novice/advanced presets and checkpoint loading.

These modules import `poker.engine.*` — the compiled `poker_engine` pybind11 module (`bindings/`) once it exists, exposing the same observation/action shapes the bound C++ objects provide. Wiring the AI layer to that module is tracked as its own phase in `tasks.md`, not assumed to be automatic.

### Frontend (deferred)
Not designed yet. When it's picked up, it gets its own design pass against whatever the engine's and bindings' real, by-then-stable API looks like — not against this document's guesses.

## Class and Object Relationships
- `GameController` owns a `Table` and manages `Player` objects — all in C++, all unchanged in spirit from the original engine design.
- `HandEvaluator` and `PotManager`/`Showdown` are used internally by `GameController` at round-end and hand-end; they're not meant to be driven directly by callers.
- The Python AI layer holds one `RLAgent` per AI seat and calls into the bound `GameController` the same way a human-input handler would: read legal actions, submit one action, read the resulting state.
- Nothing in `engine/` or `bindings/` references `ai/` or a frontend. Dependencies point one direction: frontend → bindings → engine, and ai → bindings → engine.

## Game Flow
1. A driver (currently: none yet — a test harness or a future CLI/frontend) constructs a `Table` with seats and blinds via the bindings (or, for engine-only tests, directly in C++).
2. At each hand, `GameController`:
   - Shuffles the deck and deals hole cards.
   - Posts blinds and sets active players.
   - Runs the pre-flop betting round.
   - Deals the flop, runs the flop betting round.
   - Deals the turn, runs the turn betting round.
   - Deals the river, runs the river betting round.
   - Resolves the showdown and distributes pots.
   - Rotates the dealer button.
3. For each seat's turn, the driver asks the controller for legal actions; a human-input handler or an `RLAgent.choose_action()` call decides which one to submit.
4. AI training updates happen in the Python `OnlineTrainer`, fed by hand outcomes read back through the bindings after each hand completes.

## RL Agent Design
Unchanged from the original design — this is Python-side and doesn't depend on which language the engine is written in, only on the shape of the observations it can extract.

### Observation Space
- Own hole cards encoded as numeric features.
- Community cards for the current round.
- Own stack and pot contribution.
- Current pot size and current bet to call.
- Number of active opponents and their visible stack totals.
- Current round stage (pre-flop, flop, turn, river).
- Position relative to dealer.

### Action Space
- `Fold`
- `Check` / `Call`
- `Bet` / `Raise` with a small set of sizing buckets (e.g. min, half pot, pot, all-in)

### Reward Structure
- Final chip gain or loss after each hand.
- Secondary shaping signals for preserving chips and winning pots.
- Penalties for folding strong hands or calling too much.

### Learning Algorithm
- Policy-gradient style agent (actor-critic), implemented in PyTorch.
- Update the policy using experience from recent hands.
- Entropy/epsilon-based exploration schedule.
- Online updates between hands while a game is in progress.

### Training Strategy
- Start AI agents with a baseline heuristic policy to ensure playable behavior before training accumulates.
- Collect experiences from every action into a replay buffer.
- Periodically update the policy after a small batch of hands.
- Persist policy checkpoints between sessions.

## Data Flow and Integration
- A driver (test harness today, a frontend later) triggers action requests against the bound `GameController`.
- The C++ engine validates and applies every action, regardless of who requested it.
- AI decisions are computed in Python from bound-engine state and submitted back through the same binding calls a human-input path would use.
- Training feedback runs asynchronously in the Python `OnlineTrainer` so it doesn't block whatever's driving turns forward.

## Extensibility
- Add new game variants later (Omaha, Short Deck) by extending `engine/` classes — the C++ layer is the right place for new rules, not the bindings or AI layer.
- Network play becomes more natural with this split: a server process could embed `engine/` directly and speak a wire protocol to remote frontends, without touching AI or rules code.
- Add more sophisticated AI models or tournament play without engine changes, as long as the bindings expose what's needed.
- Frontend, sound, and animation layers are entirely future work, designed against a stable engine/bindings API.

## Technology Stack
- C++20 for the engine (`engine/`), built with CMake, tested with GoogleTest (via `find_package`, falling back to `FetchContent` if not installed locally).
- pybind11 for the Python bindings (`bindings/`), fetched via CMake `FetchContent`, built only when `POKER_BUILD_PYTHON_BINDINGS=ON`.
- Python 3.11+ and PyTorch for the AI layer (`src/poker/ai/`), tested with pytest.
- Frontend stack: undecided, out of scope for this revision.

## Project Assumptions
- The first release is single-machine, local play only.
- AI training is lightweight and suitable for interactive gameplay.
- The game will support up to 10 seats with a mix of human and AI players, once a frontend exists to seat a human.
- The engine is the single source of truth for rules; every other layer is a client of it.
