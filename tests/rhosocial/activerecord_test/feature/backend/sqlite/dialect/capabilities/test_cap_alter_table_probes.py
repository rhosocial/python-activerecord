# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect/capabilities/test_cap_alter_table_probes.py
"""SQLite's ALTER TABLE probes must match what the engine actually accepts.

SQLite takes only one action per ALTER TABLE statement (a comma-joined second
action is a ``near ",": syntax error``), and it has no
``ALTER COLUMN ... SET DATA TYPE`` grammar. Core answers both probes ``True``
by default, which made the core formatter emit SQL SQLite rejects. The SQLite
dialect answers both itself; these tests pin the answers and the consequences.
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
from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
    SQLiteIntegerType,
    SQLiteTextType,
)


class TestSQLiteAlterTableProbes:
    """Neither answer is version-dependent, so assert it across the version matrix."""

    def test_multi_action_alter_table_is_unsupported(self, sqlite_dialect):
        assert sqlite_dialect.supports_multi_action_alter_table() is False

    def test_alter_column_type_is_unsupported(self, sqlite_dialect):
        assert sqlite_dialect.supports_alter_column_type() is False


class TestSQLiteTwoActionAlterStatement:
    """The core formatter must not comma-join two actions for SQLite."""

    @pytest.fixture
    def dialect(self):
        return SQLiteDialect(version=(3, 53, 0))

    @staticmethod
    def _two_add_column_statement(dialect):
        email = AddColumnAction(
            dialect,
            column=ColumnDefinition(dialect, "email", SQLiteTextType(dialect=dialect)),
        )
        age = AddColumnAction(
            dialect,
            column=ColumnDefinition(dialect, "age", SQLiteIntegerType(dialect=dialect)),
        )
        return AlterTableStatement(dialect, table=Table(dialect, "users"), actions=[email, age])

    def test_two_actions_are_semicolon_separated_not_comma_joined(self, dialect):
        sql, params = self._two_add_column_statement(dialect).to_sql()

        assert sql == (
            'ALTER TABLE "users" ADD COLUMN "email" TEXT; '
            'ALTER TABLE "users" ADD COLUMN "age" INTEGER'
        )
        assert ", ADD COLUMN" not in sql
        assert sql.count("ALTER TABLE") == 2
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
