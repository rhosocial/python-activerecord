# tests/rhosocial/activerecord_test/feature/backend/sqlite/core/conftest.py
"""SQLite executable core tests use temporary databases and shared backend state.

Declared as one parallel unit so they stay on a single xdist worker per scenario.
"""
from rhosocial.activerecord.testsuite.pytest_plugin import Declaration

DECLARATION = Declaration(
    parallel=True,
    purpose="SQLite backend execution: DML, DQL, DDL, transactions and batching",
    passes_means="executed statements produce the expected rows, schema and transaction outcomes",
    fails_means="a statement executes against the wrong connection or loses its effects",
)
