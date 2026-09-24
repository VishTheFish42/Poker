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
- `Table`: holds players, dealer position, blinds, community cards, burned cards (one burned before each of the flop, turn, and river), and pot state. (Implemented — see `engine/include/poker/table.hpp`.)
- `BettingRound`: manages action order, permissible actions, and current bets for one street. (Implemented — see `engine/include/poker/betting_round.hpp`.)
- `PotManager`: tracks the main pot and side pots. (Implemented — see `engine/include/poker/pot_manager.hpp`.)
- `Showdown`: resolves hand comparisons and pot distribution, including ties and split pots. (Implemented — see `engine/include/poker/showdown.hpp`.)
- `GameController`: owns the `Table` and orchestrates hands — button rotation, blind posting, dealing, one `BettingRound` per street, all-in runouts, showdown. The caller submits each action for `currentSeat()`; the controller checks turn order and `legalActions()` before applying it. Transitions that need no decision (closing a street, dealing the next, resolving the hand) either run immediately (`ProgressionMode::Auto`) or wait for `stepOnce()`/`advance()` (`ProgressionMode::SingleStep`), so a caller (an AI loop, tests, a future frontend) can pace them. `phase()` says which of those it's waiting on. `startHand()` optionally takes cards to deal first, for scripted hands. (Implemented — see `engine/include/poker/game_controller.hpp`.)

Each class lives as a `<name>.hpp` / `<name>.cpp` pair under `engine/include/poker/` and `engine/src/`, with a matching `engine/tests/test_<name>.cpp`.

### `bindings/` (pybind11)
- One module, `poker_engine` (`bindings/module.cpp`), wrapping the engine classes and enums the AI layer needs. (Implemented; tested by `tests/test_bindings.py`.)
- No rules logic here — if something needs a rules decision, it belongs in `engine/`, not in a binding wrapper function.
- Built only when `POKER_BUILD_PYTHON_BINDINGS=ON` is passed to CMake, so the engine and its GoogleTest suite build standalone without a Python dev environment. The module lands in `build/bindings/`, built against `.venv`'s Python by default; `tests/conftest.py` puts that directory on `sys.path`.

#### Python API
Naming follows Python conventions: snake_case members, UPPER_SNAKE enum values (`ActionType.ALL_IN`, `Street.PRE_FLOP`), and argument-free C++ getters become read-only properties. Engine exceptions map to `ValueError` (`std::invalid_argument`: illegal action, bad argument), `IndexError` (`std::out_of_range`: empty deck), and `RuntimeError` (`std::logic_error`: wrong phase, e.g. acting when no one is on the clock).

| Python | Exposes |
|---|---|
| Enums | `Suit`, `Rank`, `HandType`, `ActionType`, `PlayerStatus`, `Street`, `ProgressionMode`, `HandPhase`; `street_number(street)` |
| `Card(suit, rank)` | `suit`, `rank`, `rank_value`; `str()` gives e.g. `A♠`; hashable; `==` compares suit and rank, `<` compares rank only |
| `Deck()` | `shuffle()`, `seed(n)`, `put_on_top(cards)`, `deal_card()`, `peek_card()`, `reset()`, `remaining`, `is_empty`, `len()`, `FULL_DECK_SIZE` |
| `HandEvaluator` | static `evaluate_hand(5 cards)`, `best_hand_from_seven(7 cards)` → `Hand` (`hand_type`, `rank_value`, `kickers`, `cards`; comparable) |
| `Action(action_type, player_seat, amount=0)` | BET amount = chips put in; RAISE amount = raise *by*, on top of the call; CALL/ALL_IN amounts ignored |
| `Player(name, seat, initial_stack)` | `name`, `seat`, `stack`, `hole_cards`, `status`, `current_bet` (this hand), `is_active`, `can_act`, `has_chips` |
| `Table(num_seats)` | Seating: `add_player`, `remove_player`, `get_player(seat)`, `get_all_players()`, `get_active_players()`. Position: `button_seat`, `small_blind_seat`, `big_blind_seat`, `is_button(seat)` etc., `get_next_active_player(seat)`, `current_player_seat`. State: `street`, `community_cards`, `burned_cards`, `total_pot`, blind amounts, `deck` (live, e.g. for seeding). `MAX_PLAYERS` |
| `GameController(table, small_blind_amount, big_blind_amount, mode=AUTO)` | Hand flow: `start_hand(stacked_cards=[])`, `submit_action(action)`, `step_once()`, `advance()`, `mode` (settable). Queries: `phase`, `current_seat`, `legal_actions()` → `LegalActions`, `validate_action(action)` → reason or `None`, `betting_round` → `BettingRound` or `None`, `contributions` (`{seat: chips this hand}`), `pots` → `[Pot]`, `last_result` → `ShowdownResult` or `None`, `hand_number`, `is_hand_complete`, `table` (live) |
| `LegalActions` | `seat`, `can_fold`, `can_check`, `can_call`/`call_amount`, `can_bet`/`min_bet`/`max_bet`, `can_raise`/`min_raise`/`max_raise` (raise-by), `can_all_in`/`all_in_amount` |
| `BettingRound` | `highest_bet`, `min_raise_amount`, `player_bet_amounts` (this street), `actions`, `get_amount_to_call(seat)`, `can_check(seat)`, `is_capped(seat)`, `get_players_all_in()` |
| `ShowdownResult` / `PlayerResult` / `Pot` | `player_results`, `winners`, `is_showdown`, `total_pot` / `seat`, `name`, `hole_cards`, `best_hand` (`None` on a fold-win), `chips_won` / `amount`, `eligible_seats` |

Ownership rules, which keep Python from ever holding a dangling C++ pointer:
- **Snapshots**: `Player`s read from a `Table` and `GameController.betting_round` are copies taken when read. A seat can be emptied and a street's betting round is replaced each street, so live references could dangle. Re-read them after the game moves on.
- **Live references**: `GameController.table` and `Table.deck`, whose owners never replace them. Each keeps its owner alive.
- **The controller copies its table**: `GameController(table, ...)` works on its own copy (the C++ constructor takes `Table` by value), so seat players on the original first, then use `controller.table`.
- Table's per-hand mutators (dealing, blinds, advancing streets, pot updates) and `Player`'s chip/status mutators are not bound: only `GameController` drives a hand.

### `ai/` (Python, under `src/poker/ai/`)
- `RLAgent`: encapsulates the policy network and training loop.
- `PolicyNetwork`: neural model mapping observations to action probabilities (PyTorch).
- `ReplayBuffer`: stores experience tuples for policy updates.
- `ActionSpace`: defines fold, call/check, and raise/bet choices.
- `ObservationEncoder`: converts engine state (read through the bindings) into numeric features.
- `RewardCalculator`: computes reward signals from hand outcomes.
- `OnlineTrainer`: runs policy updates between hands during live play.
- `difficulty`: novice/advanced presets and checkpoint loading.

These modules still import the old Python engine (`poker.engine.*`), which no longer exists, so they don't import at the moment. Rewiring them onto the `poker_engine` module above is tracked as its own task in `tasks.md` (5.7), not assumed to be automatic.

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
   - Rotates the dealer button (skipping busted seats).
   - Shuffles the deck and deals hole cards.
   - Posts blinds and sets active players.
   - Runs the pre-flop betting round.
   - Deals the flop, runs the flop betting round.
   - Deals the turn, runs the turn betting round.
   - Deals the river, runs the river betting round.
   - Resolves the showdown and distributes pots.
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
- pybind11 for the Python bindings (`bindings/`), via `find_package` if installed and `FetchContent` otherwise, built only when `POKER_BUILD_PYTHON_BINDINGS=ON`.
- Python 3.11+ and PyTorch for the AI layer (`src/poker/ai/`), tested with pytest.
- Frontend stack: undecided, out of scope for this revision.

## Project Assumptions
- The first release is single-machine, local play only.
- AI training is lightweight and suitable for interactive gameplay.
- The game will support up to 10 seats with a mix of human and AI players, once a frontend exists to seat a human.
- The engine is the single source of truth for rules; every other layer is a client of it.
