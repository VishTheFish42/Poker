# Poker Game Design

## High-Level Architecture
The application is structured as three main subsystems:
1. Game Engine
2. User Interface
3. AI Agent / Reinforcement Learning

The game follows a Model-View-Controller pattern:
- Model: poker data structures and game state.
- View: PyQt/PySide desktop GUI.
- Controller: game flow coordinator and action dispatcher.

## Module Overview

### `engine`
- `Card`: Represents suit and rank.
- `Deck`: Generates and shuffles 52 cards.
- `HandEvaluator`: Computes Texas Hold'em hand strength and rank ordering.
- `Player`: Base class for seat ownership, stack size, hole cards, and status.
- `HumanPlayer`: Extends `Player` with UI-driven actions.
- `AIPlayer`: Extends `Player` with RL policy integration.
- `Table`: Holds players, dealer position, blinds, community cards, and pot state.
- `BettingRound`: Manages action order, permissible actions, and current bets.
- `PotManager`: Tracks main pot and side pots.
- `GameState`: Represents the current round, stage, and player turn.
- `GameController`: Orchestrates new hands, rounds, transitions, and showdown.

### `ui`
- `MainWindow`: Launches the application and manages view transitions.
- `LobbyView`: Collects player name, buy-in, opponent count, and settings.
- `TableView`: Displays table, players, cards, chip counts, pot, and action controls.
- `ActionPanel`: Provides fold/call/raise controls and bet sizing.
- `GameLogView`: Streams events and results.
- `ResultDialog`: Shows hand resolution and round summary.
- `SettingsDialog`: Exposes blinds, difficulty, and persistence options.

### `ai`
- `RLAgent`: Encapsulates the policy network and training loop.
- `PolicyNetwork`: Neural model mapping observations to action probabilities.
- `ReplayBuffer`: Stores experience tuples for policy updates.
- `ActionSpace`: Defines fold, call/check, and raise/bet choices.
- `ObservationEncoder`: Converts game state to numeric features.
- `RewardCalculator`: Computes reward signals from hand outcomes.
- `AIManager`: Manages multiple AI players and background updates.

## Class and Object Relationships
- `GameController` owns a `Table` and manages `Player` objects.
- Each `AIPlayer` references an `RLAgent` for action selection.
- `TableView` observes `GameState` updates from `GameController`.
- UI events invoke `GameController` methods, which validate actions via `BettingRound`.
- After each hand, `GameController` calls `HandEvaluator` and `PotManager`.

## Game Flow
1. User completes lobby setup.
2. `GameController` creates a `Table` with seats and blinds.
3. At each hand:
   - Shuffle deck and deal hole cards.
   - Post blinds and set active players.
   - Execute pre-flop betting round.
   - Deal flop and execute flop betting round.
   - Deal turn and execute turn betting round.
   - Deal river and execute river betting round.
   - Resolve showdown and distribute pots.
   - Rotate dealer and start next hand.
4. AI players choose actions via the RL policy.
5. Training updates occur between hands or in a background tick.

## UI Design
- Start screen with input fields:
  - Player name
  - Buy-in amount
  - Number of opponents
  - Difficulty selection
- Table screen features:
  - Centered community cards with card art.
  - Player seat widgets around the table.
  - Each seat shows name, stack, current bet, and status.
  - Human player panel with action buttons and bet slider.
  - Pot and current bet summary at the bottom.
  - Side panel with game log and round data.
- Visual polish:
  - Custom card images or stylized card faces.
  - Animated dealing and chip movement.
  - Smooth transitions between rounds.

## RL Agent Design

### Observation Space
The agent will observe a condensed game state, including:
- Own hole cards encoded as numeric features.
- Community cards for the current round.
- Own stack and pot contribution.
- Current pot size and current bet to call.
- Number of active opponents and their visible stack totals.
- Current round stage (pre-flop, flop, turn, river).
- Position relative to dealer.

### Action Space
The agent will choose from:
- `Fold`
- `Check` / `Call`
- `Bet` / `Raise` with a small set of sizing buckets (e.g. min, half pot, pot, all-in)

### Reward Structure
Rewards are derived from:
- Final chip gain or loss after each hand.
- Secondary shaping signals for preserving chips and winning pots.
- Penalties for folding strong hands or calling too much.

### Learning Algorithm
- Use a policy-gradient style agent such as actor-critic.
- Maintain a lightweight neural policy network in PyTorch.
- Update the policy using experience from recent hands.
- Use an epsilon or entropy-based exploration schedule.
- Support online updates between hands while the user plays.

### Training Strategy
- Start AI agents with a baseline heuristic policy to ensure playable behavior.
- Collect experiences from every action and store them in a replay buffer.
- Periodically update the policy after a small batch of hands.
- Save the policy state after each session if feasible.

## Data Flow and Integration
- UI triggers player action events.
- `GameController` validates and applies actions through the engine.
- AI decisions are requested from `AIPlayer` objects and passed back into the game loop.
- The UI refreshes after every action and stage change.
- Training feedback is emitted asynchronously to avoid blocking the UI.

## Extensibility
- Add new game variants later (Omaha, Short Deck) by extending engine classes.
- Add network play by separating the game state from the local UI.
- Add more sophisticated AI models or tournament play.
- Add sound effects, dealer voice, or animation layers.

## Technology Stack
- Python 3.11+
- PySide6 / PyQt6 for desktop UI
- PyTorch for RL model training
- Optional supporting libraries: NumPy, pandas, and image asset loaders

## Project Assumptions
- The first release is single-machine, local play only.
- AI training is lightweight and suitable for interactive gameplay.
- The game will support up to 10 seats with a mix of human and AI players.
- The UI will be styled for a sophisticated and polished desktop experience.
