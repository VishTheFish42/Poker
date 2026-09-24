"""Shared pytest fixtures."""

import os
import sys
from pathlib import Path

# Make the compiled `poker_engine` module importable straight from the CMake
# build tree (cmake -S . -B build -DPOKER_BUILD_PYTHON_BINDINGS=ON). Set
# POKER_ENGINE_BUILD_DIR to use a different build directory.
_ENGINE_DIR = Path(
    os.environ.get(
        "POKER_ENGINE_BUILD_DIR", Path(__file__).resolve().parent.parent / "build" / "bindings"
    )
)
if _ENGINE_DIR.is_dir():
    sys.path.insert(0, str(_ENGINE_DIR))
