"""Architecture Document for Poker Application

This document outlines the high-level architecture and design patterns for the three main
subsystems: Game Engine, User Interface, and Reinforcement Learning AI.

## System Overview

The Poker application consists of three tightly integrated but independently testable subsystems:

1. **Game Engine**: Core poker logic, rules enforcement, and game state management
2. **User Interface**: Desktop GUI built with PySide6 for user interaction and game visualization
3. **AI & Reinforcement Learning**: Intelligent opponents powered by neural network policies

These subsystems interact via a Model-View-Controller (MVC) pattern where:
- Model: Game Engine (game state and rules)
- View: UI (game visualization)
- Controller: GameController (orchestrates engine and AI)

---

## 1. Game Engine Architecture

### 1.1 Core Data Structures

```
Card
├── suit: CardSuit (HEARTS, DIAMONDS, CLUBS, SPADES)
├── rank: CardRank (2-10, J, Q, K, A)
└── Methods: __repr__(), __hash__(), __eq__()

Deck
├── cards: List[Card]
├── Methods: shuffle(), deal_card(), reset()

Player
├── seat: int
├── stack: int (chip count)
├── hole_cards: List[Card]
├── current_bet: int
├── status: PlayerStatus (ACTIVE, FOLDED, ALL_IN, SITTING_OUT)
├── is_human: bool
├── Methods: add_chips(), remove_chips(), receive_cards(), fold(), etc.

HumanPlayer(Player)
├── name: str
├── pending_action: Optional[Action]
├── Methods: set_action() (called by UI)

AIPlayer(Player)
├── ai_agent: RLAgent
├── difficulty: Difficulty (NOVICE, ADVANCED)
├── Methods: get_action() (calls ai_agent.select_action())

Hand (evaluation result)
├── hand_type: HandType (HIGH_CARD, PAIR, etc.)
├── rank: int (for comparison)
├── kicker_cards: List[Card] (for tie-breaking)
└── Methods: __lt__(), __eq__()

Table
├── players: List[Player]
├── dealer_seat: int
├── small_blind: int
├── big_blind: int
├── deck: Deck
├── community_cards: List[Card] (0-5 cards)
├── pots: List[Pot] (main pot + side pots)
├── button_position: int
├── current_bet: int (current bet to call)
└── Methods: (see 1.2 below)

Pot
├── amount: int
├── contributors: Dict[int, int] (seat -> amount_contributed)
└── Methods: distribute()

Action
├── action_type: ActionType (FOLD, CHECK, CALL, BET, RAISE, ALL_IN)
├── amount: int (0 for check/fold, call amount, or bet/raise amount)
└── player_seat: int

GameState
├── stage: Stage (PRE_FLOP, FLOP, TURN, RIVER, SHOWDOWN)
├── active_players: List[Player]
├── current_player: Player
├── button_position: int
├── hand_number: int
└── Methods: advance_stage(), get_remaining_players()
```

### 1.2 Game Engine Classes

#### Table
```
Class Table:
    - __init__(players, small_blind, big_blind)
    - new_hand(): Resets for a new hand
    - post_blinds(): Deducts small/big blind from players
    - deal_hole_cards(): Gives each player 2 cards
    - add_community_card(card): For flop, turn, river
    - advance_to_next_stage(): Moves from pre-flop → flop → turn → river → showdown
    - get_all_actions(player): Returns list of valid Action objects
    - apply_action(action): Updates pots and player state
    - is_hand_over(): Checks if only one player remains (all others folded)
    - is_stage_over(): Checks if all active players have acted and are even
    - rotate_button(): Moves dealer button for next hand
    - get_pot_total(): Returns sum of all pots
    - Methods for querying state (get_player_at_seat, get_next_to_act, etc.)
```

#### HandEvaluator
```
Class HandEvaluator:
    - static evaluate_hand(7_cards: List[Card]) -> Hand
      * Finds best 5-card combination from 7 cards
      * Returns Hand object with type, rank, and kickers
    
    - static compare_hands(hands: List[Hand]) -> List[int]
      * Compares multiple hands
      * Returns list of seat indices ranked by hand strength
      * Handles ties by kicker cards
    
    - static hand_rank(hand_type: HandType) -> int
      * Returns numeric rank (higher = stronger)
    
    - static is_straight(5_cards: List[Card]) -> bool
    - static is_flush(5_cards: List[Card]) -> bool
    - static has_pairs(5_cards: List[Card]) -> Tuple[int, int, int]
      * Returns counts of each rank group
```

#### BettingRound
```
Class BettingRound:
    - __init__(table, active_players, button_position)
    - get_valid_actions(player: Player) -> List[Action]
      * Returns available actions based on game state
      * (FOLD always available; CHECK if no bet; CALL if bet; BET/RAISE if funds available)
    
    - apply_action(action: Action) -> GameEventList
      * Applies action to table
      * Returns list of events for logging/UI
      * Raises exception if invalid action
    
    - is_action_required() -> bool
      * True if current player must act
    
    - get_next_actor() -> Player
      * Returns player whose turn it is
    
    - advance_turn()
      * Moves to next player who hasn't folded
    
    - is_betting_complete() -> bool
      * All active players have acted and match current bet
      * OR all but one have folded
    
    - run_to_completion(action_callback) -> None
      * Executes betting round until complete
      * Calls action_callback(player) to get actions
```

#### PotManager
```
Class PotManager:
    - __init__()
    - add_bet(seat: int, amount: int) -> None
      * Adds a bet to the current pot or creates side pot if needed
      * Handles all-in situations automatically
    
    - get_total() -> int
      * Sum of all pots
    
    - distribute(winners: List[Tuple[int, Hand]]) -> Dict[int, int]
      * Input: list of (seat, hand) tuples
      * Returns: seat -> chips_won mapping
      * Splits pots among eligible winners
    
    - get_pot_structure() -> List[Pot]
      * Returns list of Pot objects for UI display
    
    - reset() -> None
      * Clears pots for new hand
```

#### GameController
```
Class GameController:
    - __init__(players: List[Player], small_blind, big_blind)
    - new_hand() -> None
      * Initializes new hand
      * Deals hole cards
      * Posts blinds
      * Starts pre-flop betting
    
    - execute_betting_round() -> bool
      * Runs current betting round to completion
      * Returns True if hand should continue, False if all but one folded
    
    - advance_to_stage(stage: Stage) -> None
      * Deals community cards for stage
      * Resets current bet for next betting round
    
    - resolve_showdown() -> Dict[int, int]
      * Evaluates all remaining hands
      * Distributes pots
      * Returns seat -> chips mapping
    
    - handle_player_action(player: Player, action: Action) -> bool
      * Validates and applies action
      * Advances turn or stage as needed
      * Returns True if action was valid
    
    - get_game_state() -> GameState
      * Returns current state snapshot for UI/AI
    
    - is_hand_over() -> bool
```

### 1.3 Game State Flow

```
Hand Lifecycle:

1. new_hand()
   ├─ Shuffle deck
   ├─ Deal hole cards to active players
   ├─ Post blinds
   └─ Set current_player to UTG (under the gun)

2. Pre-Flop Betting Round
   ├─ Player 1 acts (UTG)
   ├─ Player 2 acts
   ├─ ... (rotate to button, then small/big blind)
   ├─ Until all active players match current bet OR all but one fold
   └─ If hand continues: advance_to_stage(FLOP)

3. Flop Betting Round
   ├─ Deal 3 community cards
   ├─ Small blind acts first
   ├─ ... (rotate through active players)
   └─ If hand continues: advance_to_stage(TURN)

4. Turn Betting Round
   ├─ Deal 1 community card (4th)
   ├─ Repeat betting round
   └─ If hand continues: advance_to_stage(RIVER)

5. River Betting Round
   ├─ Deal 1 community card (5th)
   ├─ Repeat betting round
   └─ If hand continues: resolve_showdown()

6. Showdown
   ├─ Evaluate all remaining players' hands (2 hole + 5 community)
   ├─ Determine winner(s)
   ├─ Distribute pot(s)
   └─ Rotate button and repeat
```

---

## 2. User Interface Architecture

### 2.1 View Hierarchy (PySide6)

```
MainWindow (QMainWindow)
├── MenuBar
│   ├── File
│   │   ├── New Game
│   │   ├── Settings
│   │   └── Exit
│   └── Help
│       └── About
├── StackedWidget (view switcher)
│   ├── LobbyView (QWidget)
│   │   ├── PlayerNameInput
│   │   ├── BuyInSpinBox
│   │   ├── OpponentCountSlider
│   │   ├── DifficultyCombo
│   │   └── StartButton
│   │
│   ├── TableView (QWidget)
│   │   ├── CommunityCardDisplay
│   │   │   └── CardLabel[] (5 cards max)
│   │   ├── SeatWidget[] (up to 10 seats)
│   │   │   ├── PlayerNameLabel
│   │   │   ├── StackLabel
│   │   │   ├── HoleCardDisplay (2 cards for human only)
│   │   │   ├── StatusLabel
│   │   │   └── CurrentBetLabel
│   │   ├── PotDisplay
│   │   │   └── PotLabel (main pot + side pots)
│   │   ├── ActionPanel
│   │   │   ├── FoldButton
│   │   │   ├── CheckCallButton (context-sensitive)
│   │   │   ├── RaiseButton
│   │   │   ├── BetSlider / BetSpinBox
│   │   │   └── AllInButton
│   │   ├── GameLogView
│   │   │   └── QTextEdit (read-only log)
│   │   └── StatusBar
│   │       ├── CurrentPlayerLabel
│   │       ├── StageLabel
│   │       └── TimerLabel
│   │
│   └── ResultDialog (QDialog)
│       ├── WinnerLabel
│       ├── HandTypeLabel
│       ├── PotDistributionTable
│       ├── ContinueButton
│       └── QuitButton

StatusBar
└── Settings icon (triggers SettingsDialog)
```

### 2.2 Key UI Classes

#### MainWindow
```
Class MainWindow(QMainWindow):
    - __init__(game_controller: GameController)
    - setup_ui(): Builds menu and central widget
    - show_lobby_view(): Switches to LobbyView
    - show_table_view(): Switches to TableView
    - show_result_dialog(): Shows hand results
    - connect_signals(): Connects game events to UI updates
    - on_game_state_changed(state: GameState): Refreshes table display
    - on_action_required(player: Player): Enables action buttons
    - closeEvent(): Cleanup and exit
```

#### LobbyView
```
Class LobbyView(QWidget):
    - __init__()
    - setup_ui(): Creates input fields and buttons
    - get_player_config() -> PlayerConfig
      * Returns (name, buy_in, num_opponents, difficulty)
    - on_start_clicked(): Emits signal with config
    - Signal: start_game(config)
```

#### TableView
```
Class TableView(QWidget):
    - __init__(game_controller: GameController)
    - setup_ui(): Builds table layout
    - update_from_game_state(state: GameState) -> None
      * Refreshes all displays based on game state
      * Called on each action
    
    - refresh_seats(): Updates SeatWidget displays
    - refresh_community_cards(): Shows current community cards
    - refresh_pot_display(): Shows main pot and side pots
    - refresh_action_panel(): Enables/disables buttons based on valid actions
    - refresh_game_log(): Adds new events to log
    
    - set_human_player_seat(seat: int): Highlights human player
    - show_action_required(): Highlights current player needing action
    
    - Signal: player_action(action: Action)
```

#### ActionPanel
```
Class ActionPanel(QWidget):
    - __init__()
    - setup_ui(): Creates buttons and slider
    - set_valid_actions(actions: List[Action]) -> None
      * Enables only valid action buttons
    
    - update_bet_range(min_bet: int, max_bet: int) -> None
      * Updates slider/spinbox range for raises
    
    - get_selected_action() -> Action
      * Returns action based on button clicked and slider position
    
    - on_bet_slider_changed(value): Updates label
    - on_fold_clicked(): Emit action with FOLD
    - on_call_clicked(): Emit action with CALL
    - on_raise_clicked(): Emit action with RAISE + amount
    - on_all_in_clicked(): Emit action with ALL_IN
    
    - Signal: action_selected(action: Action)
    - Signal: action_submitted()
```

#### SeatWidget
```
Class SeatWidget(QWidget):
    - __init__(seat_index: int, is_human: bool)
    - update_from_player(player: Player, is_current_player: bool) -> None
      * Updates name, stack, status, bet amount
      * Shows hole cards if human and not folded
      * Highlights if current player
    
    - set_hole_cards(cards: List[Card]): Shows/hides cards
    - set_status(status: PlayerStatus): Updates label color/text
    - highlight_current_player(): Visual emphasis
    - show_current_bet(amount: int): Displays bet amount
```

### 2.3 Signal/Slot Connections

```
UI Events → GameController Actions:

ActionPanel.action_selected → GameController.handle_player_action()
LobbyView.start_game → MainWindow.show_table_view()
MainWindow.new_game → GameController.new_hand()

GameController Events → UI Updates:

GameController.game_state_changed → TableView.update_from_game_state()
GameController.action_required → ActionPanel.set_valid_actions()
GameController.hand_complete → MainWindow.show_result_dialog()
GameController.event_logged → GameLogView.add_event()
```

### 2.4 Theming and Styling

```
Constants defined in ui/styles.py:
- CARD_WIDTH, CARD_HEIGHT (pixel dimensions)
- SEAT_RADIUS (distance from table center)
- COLORS: {PLAYER_ACTIVE, PLAYER_FOLDED, CURRENT_PLAYER, HIGHLIGHT}
- FONTS: {NORMAL, BOLD, MONO}
- Card asset paths (card images or Unicode suit symbols)
```

---

## 3. Reinforcement Learning AI Architecture

### 3.1 Observation Space

```
State Representation (numeric feature vector):
- Hole card encoding: [card1_suit, card1_rank, card2_suit, card2_rank]
- Community card encoding: 5 * [suit, rank] for each stage
  (filled with -1 if not yet dealt)
- Own stack: [own_chips]
- Pot size: [total_pot]
- Current bet to call: [call_amount]
- Opponent stacks: [opponent1_chips, opponent2_chips, ...]
- Position relative to dealer: [button_distance]
- Stage encoding: [is_preflop, is_flop, is_turn, is_river]
- Number of active opponents: [num_opponents]
- Total size: ~30-50 numeric features (varies with table size)

Encoding handled by: ai/observation.py::ObservationEncoder
Output: numpy array of shape (num_features,) normalized to [0, 1] or [-1, 1]
```

### 3.2 Action Space

```
Discrete action set:
- Fold (0)
- Check/Call (1)
- Bet/Raise (buckets 2-5):
  * Min bet (2)
  * 1/2 pot (3)
  * Full pot (4)
  * All-in (5)

Total: 6 discrete actions

Mapping handled by: ai/action_space.py
- action_code_to_engine_action(code, current_bet, stack) -> Action
- engine_action_to_code(action) -> int
```

### 3.3 Reward Structure

```
Reward Signal (per hand):
- Primary: chip_delta / initial_stack
  * +1.0 if won pot
  * -amount_lost / stack if lost
  * 0 if hand didn't complete

- Secondary (optional shaping):
  * Bonus for folding weak hands early
  * Penalty for calling too much
  * Small reward for balanced play

Calculation: ai/reward.py::RewardCalculator
- hand_result_reward(hand_outcome, chips_change, stack_size) -> float
- Clipped to [-1, 1] for stability
```

### 3.4 Policy Network

```
Neural Network Architecture (PyTorch):

class PolicyNetwork(nn.Module):
    def __init__(self, input_size=48, hidden_size=128, num_actions=6):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, num_actions)
        )
    
    def forward(self, state: Tensor) -> Tensor
        # Returns logits for each action (or Q-values)
        return self.net(state)

- Input: normalized observation vector (size ~48)
- Hidden layers: 2x ReLU layers (128 units each)
- Output: logits for 6 actions
- Loss: Policy gradient or actor-critic loss
```

### 3.5 Training Loop

```
RLAgent Training Cycle:

1. Collect Experience (per hand):
   - Observe game state → encode to features
   - Forward pass through policy network
   - Sample action using softmax + temperature
   - Execute action
   - Observe reward at end of hand
   - Store (state, action, reward) in replay buffer

2. Batch Update (after N hands):
   - Sample batch of 32 experiences from replay buffer
   - For each experience:
     * Compute loss (policy gradient or Bellman error)
     * Backprop and gradient step
   - Decay exploration rate (epsilon or temperature)

3. Policy Persistence:
   - Save model weights to file after each session
   - Load weights at game startup
```

### 3.6 AI Manager

```
Class AIManager:
    - __init__(num_agents, difficulty_levels)
    - __init_agents(): Creates RLAgent for each AI player
    - get_action_for_player(seat, game_state) -> Action
      * Query appropriate agent
      * Return action after exploration
    
    - collect_experience(seat, transition):
      * Store (state, action, reward) for training
    
    - update_all_policies():
      * Run training step for each agent
      * Called between hands
    
    - set_difficulty(seat, difficulty):
      * Adjust exploration rate or policy temperature
    
    - save_checkpoint():
      * Persist all agent policies
    
    - load_checkpoint():
      * Restore agent policies from disk
```

### 3.7 Learning Strategy

```
Curriculum and Exploration:

1. Warm-up phase (first 100 hands):
   - High exploration (epsilon ~0.5)
   - Agents play many different strategies
   
2. Training phase (hands 100-1000):
   - Epsilon decay: 0.5 → 0.1
   - Policy refines based on reward signals
   
3. Deployment phase (hands 1000+):
   - Low exploration (epsilon ~0.05)
   - Policy mostly exploits learned strategy
   - Still occasional random exploration

Difficulty levels:
- NOVICE: Higher exploration, weaker policy network
- ADVANCED: Lower exploration, trained on larger dataset

Online learning: Policy updates happen after each hand (asynchronously if needed)
```

---

## 4. Integration Architecture

### 4.1 Main Game Loop

```
Main Application Flow:

1. MainWindow.show()
   └─ LobbyView collects player config

2. GameController.new_hand()
   ├─ Table.deal_hole_cards()
   ├─ Table.post_blinds()
   └─ TableView.update_from_game_state()

3. Execute Betting Round:
   while not betting_round.is_complete():
       ├─ current_player = betting_round.get_next_actor()
       ├─ if current_player.is_human:
       │   └─ Wait for ActionPanel signal
       ├─ else (AIPlayer):
       │   ├─ observation = encode_game_state()
       │   ├─ action = ai_agent.select_action(observation)
       │   └─ Apply action
       ├─ TableView.update_from_game_state()
       └─ AIManager.collect_experience()

4. After Betting Round:
   ├─ Advance to next stage (if hand continues)
   ├─ Or resolve_showdown() if hand complete
   └─ AIManager.update_all_policies() (async/background)

5. Hand Complete:
   ├─ Show ResultDialog
   ├─ Wait for player to click "Continue"
   ├─ Rotate button and repeat
```

### 4.2 Data Flow Diagram

```
User Input (UI)
    ↓
ActionPanel event
    ↓
GameController.handle_player_action()
    ↓
Table.apply_action() + PotManager
    ↓
Game State updated
    ↓
TableView.update_from_game_state()
    ↓
Screen refresh

Parallel: AI Decision
    ↓
GameState snapshot
    ↓
ObservationEncoder
    ↓
PolicyNetwork.forward()
    ↓
Action selected
    ↓
(merges into main game flow above)

Parallel: Training
    ↓
Hand complete event
    ↓
Reward calculated
    ↓
ReplayBuffer.add_experience()
    ↓
AIManager.update_all_policies()
    ↓
PolicyNetwork.backward()
    ↓
(async, doesn't block UI)
```

### 4.3 Threading Considerations

```
Main Thread (UI):
- All PySide6 widgets and event loops
- Game state updates
- User input handling

Background Thread (Optional):
- AI policy updates (training step)
- Observation encoding (if computation-heavy)
- Experience collection
- Keep I/O off main thread (save/load policies)

Thread Safety:
- Use Qt Signals/Slots for UI updates
- Protect shared game state with locks
- Replay buffer and agent state are thread-safe
```

---

## 5. Key Design Patterns

### 5.1 Model-View-Controller
- **Model**: GameEngine (Table, BettingRound, HandEvaluator)
- **View**: UI (TableView, SeatWidget, ActionPanel)
- **Controller**: GameController (orchestrates model & AI, updates view)

### 5.2 Observer Pattern
- GameController emits signals on state changes
- UI components listen and update accordingly
- No tight coupling between engine and UI

### 5.3 Strategy Pattern
- Different AI strategies via RLAgent (vs. heuristic/rule-based in future)
- Difficulty levels change exploration/exploitation balance

### 5.4 Factory Pattern
- PlayerFactory for creating HumanPlayer or AIPlayer instances
- ActionFactory for building Action objects

### 5.5 Command Pattern
- Action objects encapsulate player decisions
- Queued and executed by GameController

---

## 6. Extensibility

### 6.1 Future Enhancements
- Add new game variants (Omaha, Short Deck) by extending engine
- Network multiplayer: Use message queues and serializable game state
- Advanced AI: Swap PolicyNetwork for larger architectures (CNN, Transformer)
- Tournament mode: Extend GameController with tournament logic
- Card graphics: Add card image assets and animated dealing

### 6.2 Plugin Architecture
- Define PlayerStrategy interface
- Allow swapping different AI implementations
- Support loading pre-trained models from disk

---

## 7. Performance Considerations

- **Observation encoding**: Vectorize using NumPy for speed
- **Hand evaluation**: Use efficient lookup tables for hand rankings
- **Policy inference**: Run on CPU (GPU not needed for small network)
- **UI updates**: Batch multiple game state changes before refresh
- **Training**: Asynchronous to avoid blocking UI

---

## Conclusion

This architecture balances:
- **Modularity**: Clear separation of concerns (engine, UI, AI)
- **Extensibility**: Easy to add variants, AI types, or features
- **Testability**: Each subsystem can be tested independently
- **Performance**: Efficient data structures and async training
- **User Experience**: Responsive UI with real-time feedback

The tight integration via signals/slots allows seamless interaction while maintaining
loose coupling between subsystems.
"""
