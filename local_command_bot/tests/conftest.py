"""Pytest configuration and shared fixtures."""

import os
import sys
import pytest
from pathlib import Path

# Ensure root of project is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.state_store import StateStore
from app.config.settings import AppSettings


@pytest.fixture
def temp_db(tmp_path: Path) -> StateStore:
    """Fixture providing an isolated SQLite state store per test."""
    db_file = tmp_path / "test_state.sqlite3"
    return StateStore(db_file)


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Fixture providing an isolated output directory."""
    out_dir = tmp_path / "test_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir
