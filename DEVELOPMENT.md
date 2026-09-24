# Development Environment Setup

## Overview
This document describes how to set up a local development environment for the Poker project, which now spans two toolchains: a C++ engine and a Python AI layer. There is no frontend yet (see `specs/tasks.md` Phase 6).

## Prerequisites
- A C++20 compiler (Apple Clang, GCC, or MSVC)
- CMake 3.21+
- GoogleTest (optional — `brew install googletest` on macOS; CMake fetches it automatically if not found)
- Python 3.11 or higher (for the AI layer only)
- Git

## Part 1: C++ Engine

### Clone and Configure
```bash
git clone https://github.com/VishTheFish42/Poker.git
cd Poker
cmake -S . -B build
```
`find_package(GTest)` is tried first; if GoogleTest isn't installed locally, CMake fetches it from source via `FetchContent` (requires network access that first time).

### Build
```bash
cmake --build build -j
```

### Run Tests
```bash
./build/engine/tests/poker_engine_tests
```
Or, using CTest (also picks up GoogleTest's per-case discovery):
```bash
ctest --test-dir build --output-on-failure
```

### Project Layout
```
engine/
├── CMakeLists.txt
├── include/poker/       # public headers (card.hpp, deck.hpp, ...)
├── src/                 # implementations
└── tests/               # GoogleTest suite (test_card.cpp, test_deck.cpp, ...)
```

### Optional: Python Bindings
The `poker_engine` pybind11 module (`bindings/`) is off by default. Create the virtualenv first (Part 2): CMake builds the module against `.venv`'s Python if it exists (override with `-DPython_EXECUTABLE=/path/to/python`). pybind11 is found via `find_package` if installed, otherwise fetched.
```bash
cmake -S . -B build -DPOKER_BUILD_PYTHON_BINDINGS=ON
cmake --build build -j
```
The module lands in `build/bindings/` (e.g. `poker_engine.cpython-311-darwin.so`). `tests/conftest.py` adds that directory to `sys.path`; set `POKER_ENGINE_BUILD_DIR` if you build elsewhere. To use it in a script: `PYTHONPATH=build/bindings python -c "import poker_engine"`.

## Part 2: Python AI Layer

### Create a Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
```

### Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements-dev.txt
```

### Run Tests
Build the bindings first (Part 1, "Optional: Python Bindings"), then:
```bash
pytest
```
This runs the bindings tests and the AI layer's tests, all against the real engine, with a coverage report for `src/poker/ai/` (configured in `pyproject.toml`).

### Code Formatting and Linting
```bash
black src/ tests/
flake8 src/ tests/
mypy src/
```

## Dependency Manifest

### C++ (fetched by CMake, not manually managed)
| Dependency | Purpose |
|---|---|
| GoogleTest | Engine unit tests |
| pybind11 | Python bindings (`poker_engine`) |

### Python Runtime (`requirements.txt`)
| Package | Purpose |
|---|---|
| torch | Neural network library for RL agents |
| numpy | Numerical computations |

### Python Development (`requirements-dev.txt`)
Adds `pytest`, `pytest-cov`, `black`, `flake8`, `mypy` on top of the runtime deps.

## Common Tasks

### Adding a New Engine Class
1. Add `engine/include/poker/<name>.hpp` and `engine/src/<name>.cpp`.
2. Add it to `add_library(poker_engine ...)` in `engine/CMakeLists.txt`.
3. Add `engine/tests/test_<name>.cpp` and list it in `engine/tests/CMakeLists.txt`.
4. Rebuild and rerun the test binary.

### Adding a New Python Dependency
1. Add it to `requirements.txt` (runtime) or `requirements-dev.txt` (dev-only).
2. `pip install -r requirements-dev.txt`.
3. Commit the updated requirements file.

### Cleaning Up
```bash
rm -rf build        # C++ build directory (safe to regenerate)
rm -rf .venv         # Python virtual environment (safe to regenerate)
```

## Troubleshooting

### CMake Can't Find GoogleTest and Has No Network Access
Install it locally first (`brew install googletest` on macOS, or your distro's package), then re-run `cmake -S . -B build` — `find_package` will pick it up without needing to fetch source.

### Python Import Errors in `src/poker/ai/`
- `No module named 'poker_engine'`: the bindings aren't built, or were built somewhere other than `build/`. Build with `-DPOKER_BUILD_PYTHON_BINDINGS=ON` or set `POKER_ENGINE_BUILD_DIR`.
- The module imports in one Python but not another: it's compiled for one interpreter version. Rebuild with `-DPython_EXECUTABLE` pointing at the Python you run.

## IDE Setup

### VS Code
- Install the C/C++ and CMake Tools extensions for engine work; the Python extension for the AI layer.
- Point CMake Tools at the top-level `CMakeLists.txt`.
- Select the Python interpreter: `.venv/bin/python`.

### CLion / Other CMake-aware IDEs
Open the repository root directly — the top-level `CMakeLists.txt` is the project file.

## Contributing
1. Create a new branch: `git checkout -b feature/your-feature`.
2. Make changes; rebuild/retest the layer(s) you touched (C++ engine and/or Python AI).
3. Format/lint whichever side you touched.
4. Commit and push, then open a Pull Request.

## References
- [CMake Documentation](https://cmake.org/cmake/help/latest/)
- [GoogleTest Documentation](https://google.github.io/googletest/)
- [pybind11 Documentation](https://pybind11.readthedocs.io/)
- [PyTorch Documentation](https://pytorch.org/docs/)
- [pytest Documentation](https://docs.pytest.org/)
