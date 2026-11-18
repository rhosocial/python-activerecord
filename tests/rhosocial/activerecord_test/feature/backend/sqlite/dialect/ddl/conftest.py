# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect/ddl/conftest.py
"""SQLite DDL tests share a real database for create/alter/drop round-trips.

Declared as one parallel unit so they stay on a single xdist worker per scenario.
"""
from rhosocial.activerecord.testsuite.pytest_plugin import Declaration

DECLARATION = Declaration(
    uses_database=True,
    parallel=True,
    purpose="SQLite DDL rendering and capability gating against a live database",
    passes_means="the rendered DDL executes and the resulting schema matches the declaration",
    fails_means="a DDL clause is accepted without support or changes the wrong schema",
)
