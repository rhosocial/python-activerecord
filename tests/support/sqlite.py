# tests/support/sqlite.py
"""The SQLite backend's test scenarios.

The scenario file holds server-side parameters only; the logical database name
comes from the test directory and is injected here.  For SQLite that name maps
to a file under the backend's single test database root.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rhosocial.activerecord.backend.impl.sqlite.backend import (
    AsyncSQLiteBackend,
    SQLiteBackend,
)
from rhosocial.activerecord.backend.impl.sqlite.config import (
    DEFAULT_PRAGMAS,
    SQLiteConnectionConfig,
)

SCENARIOS = ("default",)

DATABASE_ROOT = Path(
    os.environ.get(
        "RHS_TEST_DB_DIR",
        Path(__file__).resolve().parents[1] / ".databases",
    )
)
DATABASE_SUFFIX = ".sqlite"


@dataclass(frozen=True)
class SQLiteScenario:
    """One SQLite test scenario."""

    name: str
    backend_class: Any = SQLiteBackend
    async_backend_class: Any = AsyncSQLiteBackend

    def database_path(self, database: str) -> Path:
        return DATABASE_ROOT / f"{database}_{self.name}{DATABASE_SUFFIX}"

    def make_config(self, database: str) -> SQLiteConnectionConfig:
        return SQLiteConnectionConfig(
            database=str(self.database_path(database)),
            delete_on_close=False,
            pragmas={
                **DEFAULT_PRAGMAS,
                "foreign_keys": "OFF",
                # Test databases need throughput, not crash durability: FULL
                # makes every DDL statement fsync (~20 ms each on Windows).
                "synchronous": "NORMAL",
                "wal_checkpoint": "PASSIVE",
            },
        )

    def reset_database(self, database: str) -> None:
        path = self.database_path(database)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.unlink(missing_ok=True)


def scenario(name: str) -> SQLiteScenario:
    return SQLiteScenario(name)
