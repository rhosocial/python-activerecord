# tests/providers/pooling.py
"""Database pooling helpers for the SQLite test providers.

Under parallel (pytest-xdist) runs with a positive pool size the testsuite
prepares ``{base}_0`` .. ``{base}_{N-1}.sqlite`` files per scenario (N = pool
size = worker count), clearing any leftover tables. Each test then takes any
free slot file and uses it exclusively until it finishes. Tests are
self-contained: they drop and recreate their own tables. Serial runs keep the
previous unique-file behaviour so the serial baseline is unchanged.

The pooled file name is ``{base}_{index}.sqlite`` where ``base`` is derived
from the scenario's configured ``database`` file name (e.g.
``test_activerecord.sqlite`` -> ``test_activerecord_{index}.sqlite``), so the
pool naming follows the scenario configuration.
"""
import os
import tempfile
import uuid

from rhosocial.activerecord.testsuite.core.pool import (
    configure_pool_dir,
    pooled_database_path,
    pool_dir,
    pooling_active,
    register_base_database,
    register_pool_reset_handler,
)

from .scenarios import SCENARIO_MAP

# SQLite is the only file-based backend, so the pooled-database directory is a
# backend concern, not a testsuite option. Let the operator place the
# ``test_db_*`` files on a real disk (e.g. an ext4 mount) via environment
# variable; tmpfs/9p are unsuitable (tmpfs hides I/O, 9p blocks SQLite).
_db_pool_dir = os.environ.get("RHS_TEST_DB_DIR")
if _db_pool_dir:
    configure_pool_dir(_db_pool_dir)

# Derive each scenario's pooled-database base name from its configured
# ``database`` file name (e.g. ``test_activerecord.sqlite`` -> ``test_activerecord``).
for _scenario_name, _scenario_config in SCENARIO_MAP.items():
    _db_path = _scenario_config.get("database")
    _base = os.path.splitext(os.path.basename(_db_path))[0] if _db_path else "test_db"
    register_base_database(_scenario_name, _base)


def _reset_sqlite_database(scenario: str, db_name: str) -> None:
    """Drop all leftover tables so a pooled slot file is empty and clean.

    Called by the pool once per slot at session start so each slot starts from
    a schema-consistent, empty state. Tests then drop and recreate their own
    tables. The path is derived from ``db_name`` directly. Errors are
    swallowed: a failed reset must not hide the underlying test failure.
    """
    import sqlite3

    path = os.path.join(pool_dir(), db_name + ".sqlite")
    try:
        conn = sqlite3.connect(path)
        try:
            conn.execute("PRAGMA foreign_keys = OFF")
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            for (name,) in rows:
                conn.execute(f'DROP TABLE IF EXISTS "{name}"')
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass


register_pool_reset_handler(_reset_sqlite_database)


def resolve_database_file(scenario_name: str, suffix: str = ".sqlite") -> str:
    """
    Return the database file path used by a test for the given scenario.

    With pooling active this is the deterministic per-worker pooled file for
    the scenario (reused across tests). Otherwise a unique temporary file is
    returned, preserving the historical isolation behaviour.
    """
    pooled = pooled_database_path(scenario_name, suffix)
    if pooled is not None:
        return pooled
    return os.path.join(
        tempfile.gettempdir(),
        f"test_activerecord_{scenario_name}_{uuid.uuid4().hex}.sqlite",
    )


def should_keep_database(scenario_name: str) -> bool:
    """
    Return True when a scenario's database file must NOT be deleted after a test.

    Pooled databases are reused by subsequent tests and only removed when the
    whole pool is cleaned up at session end, so per-test cleanup must skip them.
    """
    return pooling_active()