# Poker Game Requirements

## Project Overview
Build a fully functional Texas Hold'em poker game for desktop computers using Python and a modern GUI toolkit. The game must support a complete Texas Hold'em rule set, polished visuals, player customization, and intelligent opponents powered by reinforcement learning.

## Primary Goals
- Implement a complete Texas Hold'em game engine with all official rules.
- Provide a sophisticated desktop GUI experience using PyQt/PySide.
- Allow the user to choose a player name, the number of opponents, and buy-in amount.
- Include AI opponents that learn via an RL-based approach during play.
- Make the system modular, object-oriented, and extensible.

## Functional Requirements

### Game Setup
- Allow a human user to enter a player name before starting a game.
- Let the user choose a buy-in amount and starting chip stack.
- Provide a choice for total players in the hand, supporting up to 10 total seats.
- Support configurable small and big blinds.
- Initialize a table with one dealer button, blinds, and seating.

### Gameplay Rules
- Play standard Texas Hold'em with:
  - Two private hole cards per player.
  - Pre-flop, flop, turn, and river betting rounds.
  - Dealer button rotation and blind posting.
  - Check, call, bet, raise, and fold actions.
  - Fixed-limit or pot-limit raise sizing for AI and human players.
- Implement all hand ranking rules:
  - High card, pair, two pair, three of a kind, straight, flush, full house, four of a kind, straight flush, royal flush.
- Resolve ties and split pots correctly.
- Handle side pots for all-in players.
- Automatically advance the game after each action and round.

### User Interface
- Provide a main table screen showing:
  - Community cards.
  - Each player’s chip stack, seat, and status.
  - The human player's hole cards.
  - Current pot size and current bet amounts.
  - Dealer/blind indicators.
- Provide interactive controls for the human player:
  - Fold
  - Check / Call
  - Bet / Raise
  - Quick bet sizing presets and custom input.
- Display a game log with round events, player actions, and hand outcomes.
- Allow restarting the game, adjusting settings, and exiting cleanly.

### AI Opponents
- Create AI opponents using reinforcement learning.
- AI should observe game state and choose actions each betting round.
- Use an RL training process that can run while the game is played in the background.
- Maintain per-player learning state so AI agents improve over time.
- Provide at least two difficulty tiers: novice and advanced.

### Persistence and Configuration
- Persist game settings between sessions (e.g. buy-in and player name).
- Save AI agent state between runs if practical.
- Enable a settings panel for gameplay preferences.

## Non-Functional Requirements
- Codebase must be object-oriented and modular.
- Use Python 3.11+ and PySide6 or PyQt6.
- Ensure the application is responsive and stable.
- Deliver clean, maintainable source code with clear separation between engine, AI, and UI.
- Provide documentation for the module design.

## Constraints
- Desktop-only application for macOS/Windows/Linux.
- No network multiplayer required in the initial version.
- The AI should be explainable and not require huge training datasets.
- Keep the game self-contained and runnable locally.

## Acceptance Criteria
- A user can start a new game, select player name, buy-in, and total players.
- The game runs through all Texas Hold'em stages correctly.
- Betting mechanics and pot resolution work for normal, all-in, and split pot cases.
- A graphical table interface presents the game state and player actions.
- AI opponents make decisions using an RL-based model and demonstrate learning behavior over multiple hands.
- The code is structured into reusable classes and modules.
