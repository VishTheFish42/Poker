# Project Tasks and Phases

Phases are organized around the engine / bindings / AI / frontend split described in `specs/design.md`.

## Phase 1: Project Setup and Architecture
1.1 [x] Define the repo layout: `engine/` (C++), `bindings/` (pybind11), `src/poker/ai/` (Python), `specs/`.
1.2 [x] Set up the CMake + GoogleTest toolchain for the C++ engine (`find_package` first, `FetchContent` fallback).
1.3 [x] Scaffold the pybind11 bindings CMake target (build-gated behind `POKER_BUILD_PYTHON_BINDINGS`, not yet implemented).
1.4 [x] Write `specs/requirements.md` and `specs/design.md` for the engine/bindings/AI/frontend split.

## Phase 2: Core Poker Engine (C++)
2.1 [x] Implement `Card` and `Deck` abstractions, with GoogleTest coverage.
2.2 [x] Build a `HandEvaluator` for Texas Hold'em rankings (high card through royal flush).
2.3 [x] Design `Player` and `Table` (seat) models.
2.4 [x] Implement `BettingRound` and game state management.
2.5 [x] Add blind posting (`BettingRound::initializeBlinds`) and dealer button rotation (`Table::setBlinds`/`rotateButton`).
2.6 [x] Implement `PotManager` pooling and side pot management.
2.7 [x] Add `Showdown` hand resolution and tie-breaking.

## Phase 3: Interactive Game Flow (C++)
3.1 [ ] Build `GameController` to manage hand/round progression.
3.2 [ ] Integrate actions: fold, check/call, bet, raise, all-in.
3.3 [ ] Add turn order and action validation rules.
3.4 [ ] Support both full auto-advance and single-step (`stepOnce()`) progression.
3.5 [ ] Add GoogleTest coverage for a full hand played end to end, including side-pot and all-in cases.

## Phase 4: Python Bindings
4.1 [ ] Implement the pybind11 module exposing `Card`, `Deck`, `Player`, `Table`, `GameController`, and action/result types.
4.2 [ ] Expose the query methods the AI layer needs: legal actions, stacks, pot size, stage, dealer position.
4.3 [ ] Write a pytest suite against the bound module (import it, play a scripted hand, assert results).
4.4 [ ] Document the bindings' Python-facing API in `specs/design.md` once it's real.

## Phase 5: Reinforcement Learning AI (Python)
5.1 [x] Define the AI observation space and action space.
5.2 [x] Implement one or more RL agents for computer-controlled players.
5.3 [x] Create reward logic based on hand outcomes, chips won, and decisions.
5.4 [x] Add an online training loop to update AI decisions during play.
5.5 [x] Provide difficulty modes and policy persistence.
5.6 [x] Test AI behavior in simulated training matches.
5.7 [ ] Wire `src/poker/ai/*` to the pybind11-bound C++ engine (Phase 4) and re-validate 5.1-5.6 against it.

## Phase 6: Frontend (Deferred)
6.1 [ ] Decide the frontend approach/toolkit against the finished engine + bindings API.
6.2 [ ] Design lobby, table, and result screens.
6.3 [ ] Connect the frontend to the engine (via bindings or otherwise) and to the AI layer.
6.4 [ ] Visual/audio polish.

## Phase 7: Integration and UX Polishing
Blocked on Phase 6: error handling and clean restart at the integration layer, smooth turn pacing, and result feedback, once there's a frontend to integrate.

## Phase 8: Testing and Quality Assurance
8.1 [~] GoogleTest coverage for the engine — in progress alongside Phase 2/3 (`engine/tests/`, 10 suites / 95 tests so far, covering Card/Deck/HandEvaluator/Player/Table/BettingRound/PotManager/Showdown).
8.2 [ ] Full game flow tests (all betting rounds, a complete hand) in C++ — needs `GameController` (Phase 3).
8.3 [x] Pot splitting and side-pot case coverage in C++ (`test_pot_manager.cpp`, `test_betting_round.cpp`'s incomplete-raise cases).
8.4 [ ] pytest coverage for the bindings (Phase 4.3) and the wired-up AI layer (Phase 5.7).
8.5 [ ] Manual UX tests — blocked on Phase 6.
8.6 [ ] Document how to build the engine, run its tests, build the bindings, and run AI training.

## Milestones
1. Working C++ engine with full Texas Hold'em rules and GoogleTest coverage (Phases 2-3). Phase 2's building blocks (hand evaluation, players/table, betting, pots, showdown) are done; `GameController` (Phase 3) ties them into a playable hand.
2. Python bindings that let a scripted driver play a full hand with no frontend (Phase 4).
3. AI opponents integrated against the bound engine and demonstrably learning (Phase 5.7).
4. Frontend approach chosen and a basic playable UI built against the stable engine/bindings API (Phase 6).
5. Polished, integrated desktop experience (Phase 7).

## Task Breakdown
1. [x] Task 1: Set up the C++/Python repo layout, CMake + GoogleTest toolchain, and specs.
2. [x] Task 2: Implement `Card` and `Deck` in C++.
3. [x] Task 3: Implement `HandEvaluator`.
4. [x] Task 4: Implement `Player`, `Table`, `BettingRound`, `PotManager`, `Showdown`.
5. [ ] Task 5: Implement `GameController` and full-hand GoogleTest coverage.
6. [ ] Task 6: Implement the pybind11 bindings module and its pytest suite.
7. [ ] Task 7: Wire the Python AI layer to the bound engine.
8. [ ] Task 8: Choose and design the frontend.
9. [ ] Task 9: Build the frontend against the engine/bindings/AI stack.
10. [ ] Task 10: Integration, UX polish, and final documentation.
