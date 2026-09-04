# tests/rhosocial/activerecord_test/feature/backend/ddl/test_maintenance_statements.py
"""
Tests for SQLite VACUUM / ANALYZE / ATTACH / DETACH maintenance statements.

These tests verify the SQLiteMaintenanceSupport protocol conformance,
the dialect format_* methods, version gating, and real execution against
a file-backed SQLite database.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression.vacuum import (
    SQLiteVacuumExpression,
    SQLiteAnalyzeExpression,
)
from rhosocial.activerecord.backend.impl.sqlite.expression.attach import (
    SQLiteAttachExpression,
    SQLiteDetachExpression,
)
from rhosocial.activerecord.backend.impl.sqlite.protocols import SQLiteMaintenanceSupport


@pytest.fixture
def dialect():
    """Create a SQLiteDialect with a recent version enabling VACUUM INTO."""
    return SQLiteDialect(version=(3, 40, 0))


class TestSQLiteVacuumStatement:
    def test_plain_vacuum(self, dialect):
        sql, params = dialect.format_vacuum_statement(SQLiteVacuumExpression(dialect))
        assert sql == "VACUUM"
        assert params == ()

    def test_vacuum_schema(self, dialect):
        expr = SQLiteVacuumExpression(dialect, schema="aux")
        sql, _ = dialect.format_vacuum_statement(expr)
        assert sql == 'VACUUM "aux"'

    def test_vacuum_into(self, dialect):
        expr = SQLiteVacuumExpression(dialect, into="backup.db")
        sql, _ = dialect.format_vacuum_statement(expr)
        assert sql == "VACUUM INTO 'backup.db'"

    def test_vacuum_into_escapes_quote(self, dialect):
        expr = SQLiteVacuumExpression(dialect, into="my'db")
        sql, _ = dialect.format_vacuum_statement(expr)
        assert sql == "VACUUM INTO 'my''db'"

    def test_vacuum_schema_and_into_conflict(self, dialect):
        with pytest.raises(ValueError, match="VACUUM cannot combine"):
            SQLiteVacuumExpression(dialect, schema="aux", into="x.db")

    def test_vacuum_into_version_gate(self):
        old = SQLiteDialect(version=(3, 26, 0))
        expr = SQLiteVacuumExpression(old, into="backup.db")
        with pytest.raises(UnsupportedFeatureError, match="VACUUM INTO requires SQLite 3.27.0"):
            old.format_vacuum_statement(expr)

    def test_supports_vacuum_into_version(self):
        assert SQLiteDialect(version=(3, 27, 0)).supports_vacuum_into() is True
        assert SQLiteDialect(version=(3, 26, 0)).supports_vacuum_into() is False


class TestSQLiteAnalyzeStatement:
    def test_plain_analyze(self, dialect):
        sql, params = dialect.format_analyze_statement(SQLiteAnalyzeExpression(dialect))
        assert sql == "ANALYZE"
        assert params == ()


class TestSQLiteAttachDetachStatement:
    def test_attach(self, dialect):
        expr = SQLiteAttachExpression(dialect, database="aux.db", schema="aux")
        sql, _ = dialect.format_attach_statement(expr)
        assert sql == "ATTACH DATABASE 'aux.db' AS \"aux\""

    def test_detach(self, dialect):
        expr = SQLiteDetachExpression(dialect, schema="aux")
        sql, _ = dialect.format_detach_statement(expr)
        assert sql == 'DETACH DATABASE "aux"'

    def test_attach_requires_database(self, dialect):
        with pytest.raises(ValueError, match="ATTACH DATABASE requires a database"):
            SQLiteAttachExpression(dialect, database="", schema="aux")

    def test_attach_requires_schema(self, dialect):
        with pytest.raises(ValueError, match="ATTACH DATABASE requires a schema"):
            SQLiteAttachExpression(dialect, database="aux.db", schema="")

    def test_detach_requires_schema(self, dialect):
        with pytest.raises(ValueError, match="DETACH DATABASE requires a schema"):
            SQLiteDetachExpression(dialect, schema="")


class TestSQLiteMaintenanceProtocolConformance:
    def test_dialect_implements_protocol(self, dialect):
        assert isinstance(dialect, SQLiteMaintenanceSupport)

    def test_capability_switches(self, dialect):
        assert dialect.supports_vacuum() is True
        assert dialect.supports_analyze() is True
        assert dialect.supports_attach() is True
        assert dialect.supports_detach() is True


class TestSQLiteMaintenanceIntegration:
    def test_vacuum_analyze_attach_detach_real(self, sqlite_file_backend):
        backend = sqlite_file_backend
        dialect = backend.dialect

        backend.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
        backend.execute("INSERT INTO items (name) VALUES (?)", ("a",))

        backend.execute(dialect.format_vacuum_statement(SQLiteVacuumExpression(dialect))[0])
        backend.execute(dialect.format_analyze_statement(SQLiteAnalyzeExpression(dialect))[0])

        row = backend.fetch_one("SELECT count(*) AS count FROM items")
        assert row["count"] == 1

    def test_attach_detach_roundtrip(self, sqlite_file_backend, tmp_path):
        backend = sqlite_file_backend
        dialect = backend.dialect

        other_db = tmp_path / "other.db"
        other_db.write_bytes(b"")

        attach_sql, _ = dialect.format_attach_statement(
            SQLiteAttachExpression(dialect, database=str(other_db), schema="other")
        )
        backend.execute(attach_sql)

        detach_sql, _ = dialect.format_detach_statement(
            SQLiteDetachExpression(dialect, schema="other")
        )
        backend.execute(detach_sql)