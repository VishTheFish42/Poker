"""Module Layout for Poker Application

This document defines the main module structure and the responsibilities of each module.

Project Structure:
    poker/
    ├── engine/
    │   ├── __init__.py
    │   ├── card.py           # Card and Deck classes
    │   ├── hand_evaluator.py # Hand ranking and evaluation
    │   ├── player.py         # Player and HumanPlayer, AIPlayer base classes
    │   ├── table.py          # Table and game state
    │   ├── betting.py        # BettingRound and action validation
    │   ├── pot.py            # PotManager and side pot handling
    │   └── game_controller.py # GameController orchestration
    │
    ├── ui/
    │   ├── __init__.py
    │   ├── main_window.py    # MainWindow and app launcher
    │   ├── lobby_view.py     # Lobby for player setup and settings
    │   ├── table_view.py     # Main table UI and seat widgets
    │   ├── action_panel.py   # Action buttons and bet sizing
    │   ├── game_log.py       # Game event log display
    │   ├── result_dialog.py  # Hand result display
    │   ├── settings_dialog.py # Settings and preferences
    │   └── styles.py         # CSS and visual styling
    │
    ├── ai/
    │   ├── __init__.py
    │   ├── action_space.py       # Action definitions and encoding
    │   ├── observation.py        # State observation and encoding
    │   ├── reward.py             # Reward calculation
    │   ├── policy_network.py     # Neural network policy
    │   ├── replay_buffer.py      # Experience storage
    │   ├── agent.py              # RLAgent class
    │   └── ai_manager.py         # Multi-agent coordination
    │
    └── utils/
        ├── __init__.py
        └── constants.py          # Game constants and configuration

Module Responsibilities:

## engine/card.py
- Card: Represents a single card (suit, rank)
- Deck: Manages shuffling and dealing
- CardRank, CardSuit: Enums for card properties

## engine/hand_evaluator.py
- HandEvaluator: Static methods to rank 5-card or 7-card poker hands
- HandRank: Enum for hand types (high card, pair, two pair, etc.)
- compare_hands(): Compares multiple hands and returns rankings

## engine/player.py
- Player: Base class with seat, stack, hole cards, status
- HumanPlayer: Extends Player, tracks pending actions and UI events
- AIPlayer: Extends Player, uses RLAgent for action selection

## engine/table.py
- Table: Manages seats, players, dealer position, blinds, community cards, pots
- GameState: Enum for round stages (pre-flop, flop, turn, river, showdown)
- Table methods: deal_hole_cards(), post_blinds(), add_community_card(), etc.

## engine/betting.py
- BettingRound: Manages turn order, valid actions, current bet amounts
- Action: Enum for action types (fold, check, call, bet, raise, all-in)
- BettingRound methods: get_valid_actions(), apply_action(), advance_turn()

## engine/pot.py
- PotManager: Tracks main pot and side pots for all-in situations
- Pot: Represents a single pot and eligible contributors
- distribute_winnings(): Calculates and distributes pot shares

## engine/game_controller.py
- GameController: Orchestrates the game loop and round progression
- new_hand(): Initializes a new hand
- execute_betting_round(): Runs one betting round to completion
- resolve_showdown(): Evaluates hands and distributes pots
- handle_player_action(): Processes human or AI action

## ui/main_window.py
- MainWindow: Top-level application window using PySide6
- Manages view transitions (lobby → table → results)
- Coordinates with GameController

## ui/lobby_view.py
- LobbyView: Collects player name, buy-in, opponent count, difficulty
- Emits signals when game is ready to start
- Displays current settings

## ui/table_view.py
- TableView: Main game display with table layout
- SeatWidget: Displays individual player info, cards, and status
- CommunityCardDisplay: Shows flop, turn, river
- PotDisplay: Shows current pot and bets

## ui/action_panel.py
- ActionPanel: Fold, Call, Raise, Bet buttons
- BetSlider: Custom widget for bet sizing
- Emits action signals to GameController

## ui/game_log.py
- GameLogView: Scrollable text area for game events
- log_action(): Appends action messages
- log_hand_result(): Displays hand outcome

## ui/result_dialog.py
- ResultDialog: Modal showing hand resolution
- Shows winning player(s), hand type, pot distribution
- Offers "Continue" or "Restart" options

## ui/settings_dialog.py
- SettingsDialog: Modal for configuring blinds, difficulty, UI preferences
- Persists settings to local config file

## ui/styles.py
- CSS/styling definitions for the application
- Color schemes, fonts, layout parameters
- Card image asset paths

## ai/action_space.py
- ActionSpace: Enum or class for discrete actions
- action_to_enum(): Converts action objects to numeric codes
- enum_to_action(): Reverse mapping
- get_action_size(): Total number of possible actions

## ai/observation.py
- ObservationEncoder: Converts game state to numeric features
- encode_state(): Returns a numpy array of game features
- Includes: own cards, community cards, stack sizes, pot, position, etc.

## ai/reward.py
- RewardCalculator: Computes reward signals for RL training
- hand_reward(): Reward based on hand outcome
- chip_reward(): Reward based on chip change
- decision_reward(): Optional shaping for decision quality

## ai/policy_network.py
- PolicyNetwork: PyTorch neural network module
- forward(): Maps observation to action logits or Q-values
- Supports both policy-gradient and value-based approaches

## ai/replay_buffer.py
- ReplayBuffer: Stores transitions (state, action, reward, next_state)
- add_experience(): Appends new experience
- sample_batch(): Returns a random batch for training
- Supports prioritized sampling if needed

## ai/agent.py
- RLAgent: Encapsulates policy and training logic
- select_action(): Chooses action given game state
- update(): Training step using collected experiences
- save_policy(): Persists model weights
- load_policy(): Restores model weights

## ai/ai_manager.py
- AIManager: Coordinates multiple AI agents
- update_policies(): Batch training for all AI players
- get_agent_action(): Queries an agent for its next move
- manage_exploration(): Handles epsilon decay and exploration schedule

## utils/constants.py
- Game configuration: num_suits, num_ranks, blinds, etc.
- UI configuration: window dimensions, colors, fonts
- RL configuration: learning rate, batch size, buffer capacity, etc.

Integration Points:

1. GameController calls table.execute_betting_round()
2. BettingRound asks for actions from each player
3. For AIPlayer: calls ai_agent.select_action(observation)
4. For HumanPlayer: waits for UI signal from ActionPanel
5. After each action: UI refreshes via TableView
6. End of hand: GameController calls pot_manager.distribute_winnings()
7. RL training: AIManager updates policies after hand is complete

Data Flow:

UI (ActionPanel) → GameController → BettingRound → Player
GameState → ObservationEncoder → RLAgent → Action
Hand Result → RewardCalculator → ReplayBuffer → PolicyNetwork.update()

"""
