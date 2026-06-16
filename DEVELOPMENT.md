# Development Environment Setup

## Overview
This document describes how to set up a local development environment for the Poker project.

## Prerequisites
- Python 3.11 or higher
- Git
- pip (Python package manager)
- macOS, Windows, or Linux

## Step 1: Clone the Repository

```bash
git clone https://github.com/VishTheFish42/Poker.git
cd Poker
```

## Step 2: Create a Virtual Environment

A virtual environment isolates project dependencies from your system Python.

```bash
python3 -m venv .venv
```

### Activate the Virtual Environment

**On macOS/Linux:**
```bash
source .venv/bin/activate
```

**On Windows (PowerShell):**
```bash
.venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```bash
.venv\Scripts\activate.bat
```

You should see `(.venv)` in your terminal prompt when activated.

## Step 3: Upgrade pip

```bash
pip install --upgrade pip
```

## Step 4: Install Project Dependencies

### For Runtime
Install core dependencies required to run the game:

```bash
pip install -r requirements.txt
```

### For Development (Recommended)
Install additional development tools including testing, linting, and formatting:

```bash
pip install -r requirements-dev.txt
```

## Step 5: Verify Installation

Test that the environment is set up correctly:

```bash
python -c "import PySide6; import torch; import numpy; print('All dependencies imported successfully!')"
```

To verify the application can start:
```bash
python main.py
```

## Project Structure

```
Poker/
├── .venv/                    # Virtual environment (created)
├── src/poker/               # Main package
│   ├── engine/              # Game logic
│   ├── ui/                  # User interface
│   ├── ai/                  # AI and RL agents
│   └── utils/               # Utilities
├── tests/                   # Test suite
├── specs/                   # Project specifications
├── main.py                  # Application entry point
├── requirements.txt         # Runtime dependencies
├── requirements-dev.txt     # Development dependencies
├── pyproject.toml           # Project metadata and config
├── .gitignore               # Git ignore patterns
└── README.md                # Project overview
```

## Dependency Manifest

### Runtime Dependencies (`requirements.txt`)

| Package | Version | Purpose |
|---------|---------|---------|
| PySide6 | >=6.6 | Desktop GUI framework |
| torch | >=2.2 | Neural network library for RL agents |
| numpy | >=2.0 | Numerical computations |

### Development Dependencies (`requirements-dev.txt`)

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=7.0 | Unit testing framework |
| pytest-cov | >=4.0 | Code coverage reporting |
| black | >=23.0 | Code formatter |
| flake8 | >=6.0 | Linter for code quality |
| mypy | >=1.0 | Static type checker |
| sphinx | >=5.0 | Documentation generator |

## Development Workflow

### Running Tests

```bash
pytest tests/
```

Run with coverage report:
```bash
pytest --cov=src/poker tests/
```

### Code Formatting

Format code with Black:
```bash
black src/ tests/
```

### Linting

Check code quality with Flake8:
```bash
flake8 src/ tests/
```

Check type hints with mypy:
```bash
mypy src/
```

### Running the Application

```bash
python main.py
```

### Building Documentation

```bash
cd docs/
make html
```

## Common Tasks

### Adding a New Dependency

1. Add the package to `requirements.txt` or `requirements-dev.txt`
2. Run `pip install -r requirements.txt` (or requirements-dev.txt)
3. Commit the updated requirements file to git

### Deactivating the Virtual Environment

```bash
deactivate
```

### Cleaning Up

Remove the virtual environment (safe to regenerate):
```bash
rm -rf .venv
```

Clear pip cache (optional):
```bash
pip cache purge
```

## Environment Variables

Optional environment variables for configuration (create a `.env` file in the project root):

```
# Game Configuration
POKER_SMALL_BLIND=1
POKER_BIG_BLIND=2
POKER_INITIAL_STACK=1000

# AI Configuration
POKER_AI_DIFFICULTY=ADVANCED
POKER_RL_LEARNING_RATE=0.001
POKER_RL_BUFFER_SIZE=10000

# UI Configuration
POKER_THEME=DARK
```

## Troubleshooting

### Virtual Environment Not Activating
- Ensure the path to `.venv` is correct
- Check that Python 3.11+ is installed: `python --version`
- Try recreating the virtual environment

### Import Errors
- Verify all dependencies are installed: `pip list`
- Try reinstalling: `pip install --force-reinstall -r requirements.txt`
- Check Python version: `python --version` (should be 3.11+)

### PySide6 GUI Not Starting
- On Linux, you may need additional system libraries (Qt6 development files)
- On macOS with Apple Silicon, ensure Python is installed for your architecture

### Torch Installation Issues
- If PyTorch installation is slow or fails, consider using a specific wheel:
  ```bash
  pip install torch::https://download.pytorch.org/whl/cpu/torch-2.2.2+cpu-cp311-cp311-...whl
  ```

## IDE Setup

### VS Code
1. Install the Python extension
2. Select the interpreter: `.venv/bin/python`
3. Recommended extensions:
   - Python
   - PyLance
   - Flake8
   - Black Formatter
   - Pytest Explorer

### PyCharm
1. Go to Settings → Project → Python Interpreter
2. Click the gear icon and select "Add"
3. Select "Existing Environment" and choose `.venv/bin/python`

## Contributing

When making changes:
1. Create a new branch: `git checkout -b feature/your-feature`
2. Make changes and run tests: `pytest tests/`
3. Format code: `black src/ tests/`
4. Lint: `flake8 src/ tests/`
5. Commit and push: `git commit -m "..." && git push origin feature/your-feature`
6. Open a Pull Request on GitHub

## References

- [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)
- [PySide6 Documentation](https://doc.qt.io/qtforpython/)
- [PyTorch Documentation](https://pytorch.org/docs/)
- [pytest Documentation](https://docs.pytest.org/)
