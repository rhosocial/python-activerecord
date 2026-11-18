# tests/rhosocial/activerecord_test/feature/backend/sqlite/cli/conftest.py
"""SQLite CLI tests share named connections and the working directory.

Declared as one parallel unit so they stay on a single xdist worker per scenario.
"""
from rhosocial.activerecord.testsuite.pytest_plugin import Declaration

DECLARATION = Declaration(
    uses_database=True,
    parallel=True,
    purpose="SQLite CLI commands over named connections and local files",
    passes_means="a command renders, executes and prints the documented result",
    fails_means="a command silently misses its database or prints the wrong shape",
)
