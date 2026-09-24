# Poker

A Texas Hold'em poker engine written in C++, with reinforcement-learning AI opponents in Python (PyTorch). The frontend is not built yet — see `specs/tasks.md`.

## Project Overview
- **Engine (`engine/`, C++20)** — the full Texas Hold'em rule set: cards, deck, hand evaluation, betting rounds, blinds, pot/side-pot management, showdown, and a game controller. Built with CMake, tested with GoogleTest. Has no dependency on Python or any UI.
- **Bindings (`bindings/`)** — a pybind11 module, `poker_engine`, exposing the engine's public API to Python. Build-gated behind a CMake option so the engine builds and tests standalone.
- **AI (`src/poker/ai/`, Python)** — RL agents (PyTorch) that drive the engine through the bindings. The agents, policy network, reward logic, and training loop are implemented; wiring them to the engine bindings is tracked in `specs/tasks.md`.
- **Frontend** — not designed yet. It will be built once the engine and AI layers are stable, against their real public API.

See `specs/requirements.md` for scope, `specs/design.md` for the architecture, and `specs/tasks.md` for what's implemented so far.

## Building the Engine
```bash
cmake -S . -B build
cmake --build build -j
./build/engine/tests/poker_engine_tests
```
GoogleTest is picked up via `find_package` if already installed (`brew install googletest` on macOS); otherwise CMake fetches it automatically via `FetchContent`.

## Python Bindings and AI Layer
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cmake -S . -B build -DPOKER_BUILD_PYTHON_BINDINGS=ON
cmake --build build -j
pytest tests/test_bindings.py
```
Note: `src/poker/ai/` still imports the old Python engine, so its tests fail to import until Phase 5.7 in `specs/tasks.md` rewires it onto `poker_engine`; until then, run the bindings tests on their own as above.

## Project Structure
- `engine/` — C++ rules engine, headers under `include/poker/`, sources under `src/`, GoogleTest suite under `tests/`.
- `bindings/` — pybind11 module `poker_engine` (`module.cpp`).
- `src/poker/ai/` — Python RL agents, policy network, reward logic, replay buffer, online trainer.
- `tests/` — pytest suites for the bindings (`test_bindings.py`) and the AI layer.
- `specs/` — `requirements.md`, `design.md`, `tasks.md`: the source of truth for scope and progress.

## Development Workflow
- Use `specs/` as the single source of truth for requirements, design, and task status.
- Implement the engine first (Phase 2-3), then the bindings (Phase 4), then re-integrate the AI layer (Phase 5.7), then design the frontend (Phase 6).
- Keep the engine free of Python/AI/UI concepts; keep the AI layer free of rules logic the engine already owns.

## Future Work
- Wire the AI layer to the bindings.
- Design and build a new frontend.
- Sound/visual polish, settings persistence, tournament mode — all deferred until the above land.
