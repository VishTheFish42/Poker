# Poker

A desktop Texas Hold'em poker game built in Python with a sophisticated UI and reinforcement learning AI opponents.

## Project Overview
This project implements a complete Texas Hold'em experience:
- Full poker engine with hole cards, community cards, blinds, betting rounds, and showdown.
- Object-oriented architecture for the game engine, UI, and AI subsystems.
- Desktop GUI using PyQt/PySide for a polished and interactive table experience.
- Reinforcement learning-based AI opponents that learn and improve over time.
- Configurable player name, buy-in amount, player count, and difficulty.

## Key Features
- Complete Texas Hold'em rules:
  - Pre-flop, flop, turn, and river betting rounds
  - Check, call, bet, raise, fold
  - Blind posting, dealer rotation, and pot management
  - Hand ranking and split-pot resolution
- Modern desktop UI with a table view, player seats, community cards, action controls, and game log.
- AI players driven by an RL policy for dynamic behavior.
- Modular architecture with clear separation of engine, UI, and AI logic.

## Project Structure
- `specs/requirements.md` — project requirements and acceptance criteria.
- `specs/tasks.md` — task breakdown and phase numbering for implementation.
- `specs/design.md` — architecture and design details.

## Recommended Stack
- Python 3.11+
- PySide6 or PyQt6 for GUI
- PyTorch for reinforcement learning
- NumPy for numeric utilities

## Setup
1. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install pyqt6 torch numpy
   ```
3. Run the application after implementation:
   ```bash
   python main.py
   ```

## Development Workflow
- Use the `specs/` folder as the single source of truth for requirements, tasks, and design.
- Implement the game engine first, then the UI, then the RL AI.
- Keep the engine and AI logic separate from the UI for testability and maintainability.

## Future Work
- Add card art, animations, and sound effects.
- Support AI state persistence between sessions.
- Add tournament mode and multiple game variants.
- Add networked multiplayer.

## Notes
This repository is currently in design phase. The detailed implementation will follow the tasks and design specified in `specs/tasks.md` and `specs/design.md`.
