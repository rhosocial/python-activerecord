# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect/capabilities/test_cap_alter_table_probes.py
"""SQLite's ALTER TABLE probes must match what the engine actually accepts.

SQLite takes only one action per ALTER TABLE statement (a comma-joined second
action is a ``near ",": syntax error``), and it has no
``ALTER COLUMN ... SET DATA TYPE`` grammar. Core answers both probes ``True``
by default; the SQLite dialect answers both itself, and the formatter now
fails fast on a multi-action statement rather than emitting an unexecutable
semicolon-joined string (one expression = one SQL statement). These tests pin
the answers and the consequences.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    AlterTableStatement,
    ColumnDefinition,
)
from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
    AddColumnAction,
    AlterColumnAction,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression.types.types import (
    SQLiteIntegerType,
    SQLiteTextType,
)


class TestSQLiteAlterTableProbes:
    """Neither answer is version-dependent, so assert it across the version matrix."""

    def test_alter_column_type_is_unsupported(self, sqlite_dialect):
        assert sqlite_dialect.supports_alter_column_type() is False


class TestSQLiteTwoActionAlterStatement:
    """The core formatter refuses two actions, for every dialect."""

    @pytest.fixture
    def dialect(self):
        return SQLiteDialect(version=(3, 53, 0))

    @staticmethod
    def _action_list_statement(dialect):
        email = AddColumnAction(
            dialect,
            column=ColumnDefinition(dialect, "email", SQLiteTextType(dialect=dialect)),
        )
        age = AddColumnAction(
            dialect,
            column=ColumnDefinition(dialect, "age", SQLiteIntegerType(dialect=dialect)),
        )
        return AlterTableStatement(dialect, table=Table(dialect, "users"), action=[email, age])

    def test_single_action_still_renders(self, dialect):
        """A one-action statement is unaffected — it is still one SQL statement."""
        action = AddColumnAction(
            dialect,
            column=ColumnDefinition(dialect, "email", SQLiteTextType(dialect=dialect)),
        )
        sql, params = AlterTableStatement(
            dialect, table=Table(dialect, "users"), action=action
        ).to_sql()
        assert sql == 'ALTER TABLE "users" ADD COLUMN "email" TEXT'
        assert sql.count("ALTER TABLE") == 1
        assert params == ()

    def test_set_data_type_raises_instead_of_emitting_invalid_sql(self, dialect):
        action = AlterColumnAction(
            dialect,
            "c",
            "SET DATA TYPE",
            new_value=SQLiteTextType(dialect=dialect),
        )
        with pytest.raises(UnsupportedFeatureError):
            dialect.format_alter_column_action(action)
