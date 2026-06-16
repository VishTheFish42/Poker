# Project Tasks and Phases

## Phase 1: Project Setup and Architecture
1.1 [x] Create the project repository structure.
1.2 [x] Choose and install the Python GUI toolkit and ML library.
1.3 [x] Define the main module layout.
1.4 [x] Draft the architecture for game engine, UI, and AI.
1.5 [x] Create a development environment and dependency manifest.

## Phase 2: Core Poker Engine
2.1 [x] Implement card and deck abstractions.
2.2 Build a hand evaluator for Texas Hold'em rankings.
2.3 Design player and seat models.
2.4 Implement game state management and betting rounds.
2.5 Add blind posting and dealer button rotation.
2.6 Implement pot pooling and side pot management.
2.7 Add hand showdown resolution and tie-breaking.

## Phase 3: Interactive Game Flow
3.1 Build the game controller to manage round progression.
3.2 Integrate user actions: fold, check/call, bet, raise.
3.3 Add turn order and action validation rules.
3.4 Handle automatic round advancement when players act.
3.5 Implement human player prompts and action feedback.

## Phase 4: GUI Implementation
4.1 Create the main application window.
4.2 Build screens for the lobby, table, and end-of-hand results.
4.3 Display seat layout, chip stacks, community cards, and player names.
4.4 Add interactive buttons for player actions.
4.5 Implement a game log and status panel.
4.6 Add UI controls for buy-in, blinds, and restart options.
4.7 Polish the visuals with card art, animations, and layout styling.

## Phase 5: Reinforcement Learning AI
5.1 Define the AI observation space and action space.
5.2 Implement one or more RL agents for computer-controlled players.
5.3 Create reward logic based on hand outcomes, chips won, and decisions.
5.4 Add an online training loop to update AI decisions during play.
5.5 Provide difficulty modes and policy persistence.
5.6 Test AI behavior in simulated training matches.

## Phase 6: Integration and UX Polishing
6.1 Connect the game engine to the UI.
6.2 Ensure the human player and AI opponents use the same game loop.
6.3 Add error handling, validation, and clean restart behavior.
6.4 Tune UI updates for smooth gameplay.
6.5 Add sound / visual feedback and result dialogs if desired.

## Phase 7: Testing and Quality Assurance
7.1 Write unit tests for the card deck, hand evaluator, and betting engine.
7.2 Test full game flows, including all betting rounds.
7.3 Validate pot splitting and side pot cases.
7.4 Test AI decision quality and reward signals.
7.5 Perform manual UX tests on the desktop UI.
7.6 Document how to run the app and how AI training behaves.

## Milestones
1. Working game engine with Texas Hold'em rules.
2. Basic playable UI showing table state and player actions.
3. AI opponents integrated and making decisions.
4. RL training loop active and model behavior improving.
5. Polished desktop experience with settings and restart flow.

## Task Breakdown
1. [x] Task 1: Setup repo, dependencies, and environment.
2. Task 2: Implement `Card`, `Deck`, `HandEvaluator`, `Player`, `Table`, `GameEngine`.
3. Task 3: Build `GameController` and betting round logic.
4. Task 4: Design the launch lobby and settings interface.
5. Task 5: Implement the main table UI and player action widgets.
6. Task 6: Design and implement RL-based `AIPlayer` and `RLAgent`.
7. Task 7: Connect UI controls to game engine and AI logic.
8. Task 8: Add training persistence and replay experience storage.
9. Task 9: Write tests and finalize documentation.
