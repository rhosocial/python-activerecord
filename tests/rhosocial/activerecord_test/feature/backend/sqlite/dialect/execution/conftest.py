# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect/execution/conftest.py
"""Executable SQLite statement tests share backend fixtures.

Declared as one parallel unit so they stay on a single xdist worker per scenario.
"""
from rhosocial.activerecord.testsuite.pytest_plugin import Declaration

DECLARATION = Declaration(
    uses_database=True,
    parallel=True,
    purpose="Executable SQLite statements, from capability probes to recursive-CTE examples",
    passes_means="the statement runs on the real engine and returns the expected result",
    fails_means="a capability is advertised but the statement cannot actually execute",
)
