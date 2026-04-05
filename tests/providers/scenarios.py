# tests/providers/scenarios.py
"""Simplified test scenario configuration mapping table for SQLite backend."""

import os
import tempfile
from typing import Dict, Any, Tuple, Type
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

# Mapping table: scenario name -> config dict (SQLite only)
SCENARIO_MAP: Dict[str, Dict[str, Any]] = {}

def register_scenario(name: str, config: Dict[str, Any]):
    """Register an SQLite test scenario."""
    SCENARIO_MAP[name] = config

def get_scenario(name: str) -> Tuple[Type[SQLiteBackend], SQLiteConnectionConfig]:
    """
    Retrieves the backend class and a connection configuration object for a given
    scenario name. This is called by the provider to set up the database for a test.
    """
    if name not in SCENARIO_MAP:
        name = "default"  # Fallback to the default scenario if not found.

    # Unpack the configuration dictionary into the dataclass constructor.
    config = SQLiteConnectionConfig(**SCENARIO_MAP[name])
    return SQLiteBackend, config

def get_enabled_scenarios() -> Dict[str, Any]:
    """
    Returns the map of all currently enabled scenarios. The testsuite's conftest
    uses this to parameterize the tests, causing them to run for each scenario.
    """
    return SCENARIO_MAP

def _register_default_scenarios():
    """
    Registers the default scenarios supported by this SQLite backend.

    Available scenarios:
    - default: Standard file-based temporary database
    - tempfile: Alias for default (explicit reference)

    All scenarios use FILE-BASED database because:
    1. In-memory databases cannot be shared across processes (WorkerPool)
    2. File-based database exposes more real-world issues
    """
    temp_dir = tempfile.gettempdir()

    # Default scenario: file-based temporary database
    register_scenario("default", {
        "database": os.path.join(temp_dir, "test_activerecord.sqlite"),
        "delete_on_close": True
    })

    # Also register as "tempfile" for explicit reference
    register_scenario("tempfile", {
        "database": os.path.join(temp_dir, "test_activerecord_tempfile.sqlite"),
        "delete_on_close": True
    })

# Register default scenarios on module load
_register_default_scenarios()