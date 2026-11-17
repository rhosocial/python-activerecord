# tests/rhosocial/activerecord_test/feature/backend/sqlite/extensions/conftest.py
"""SQLite extension tests create virtual tables and touch PRAGMA state.

Declared as one parallel unit so they stay on a single xdist worker per scenario.
"""
from rhosocial.activerecord.testsuite.pytest_plugin import Declaration

DECLARATION = Declaration(
    parallel=True,
    purpose="SQLite virtual tables, PRAGMA surfaces and extension capabilities",
    passes_means="the extension is available and its table or pragma behaves as declared",
    fails_means="an unsupported extension is advertised or a virtual table leaks state",
)
