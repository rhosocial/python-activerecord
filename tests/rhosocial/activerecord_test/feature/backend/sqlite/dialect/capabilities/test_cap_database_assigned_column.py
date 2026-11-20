# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect/capabilities/test_cap_database_assigned_column.py
"""SQLite's two answers about a database-assigned integer column.

SQLite has neither an ``AUTO_INCREMENT`` token nor a ``GENERATED ... AS
IDENTITY`` clause, so the two *mechanism* probes answer ``False``.  The
*capability* is nevertheless there: an ``INTEGER PRIMARY KEY`` is numbered by
the rowid alias when the caller omits the value.  The answers therefore differ
on the same dialect, which is the reason the capability and the mechanism are
separate probes rather than one.
"""

from rhosocial.activerecord.backend.dialect.protocols import (
    DatabaseAssignedColumnSupport,
)


def _dialect():
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

    return SQLiteDialect()


def test_capability_is_declared():
    """The dialect satisfies the protocol that declares the question."""
    assert isinstance(_dialect(), DatabaseAssignedColumnSupport)


def test_capability_is_yes_though_the_markers_are_no():
    """The database supplies the value; it just has no marker to spell it with."""
    dialect = _dialect()
    assert dialect.supports_database_assigned_integer_column() is True
    assert dialect.supports_auto_increment_column() is False
    assert dialect.supports_identity_column() is False
