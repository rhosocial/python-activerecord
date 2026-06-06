# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_alter_table_integration.py
"""
Integration tests for ALTER TABLE operations via the expression system.

These tests exercise AlterTableExpression and its action subclasses against
a real SQLite database, then use the introspector to verify the schema was
actually modified. This validates the end-to-end correctness of the
Expression -> Dialect -> SQL -> Database -> Introspector pipeline.
"""

import pytest

from rhosocial.activerecord.backend.expression.statements import (
    CreateTableExpression,
    AlterTableExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)
from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
    AddColumn,
    DropColumn,
    RenameColumn,
    AddTableConstraint,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    TableConstraint,
    TableConstraintType,
)
from rhosocial.activerecord.backend.introspection.types import ColumnNullable
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend


@pytest.fixture
def backend_with_users(sqlite_backend: SQLiteBackend) -> SQLiteBackend:
    """Create a backend with a simple 'users' table for ALTER TABLE tests."""
    create_expr = CreateTableExpression(
        dialect=sqlite_backend.dialect,
        table="users",
        columns=[
            ColumnDefinition(
                "id",
                "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)],
            ),
            ColumnDefinition("name", "TEXT"),
        ],
    )
    sqlite_backend.execute(*create_expr.to_sql())
    return sqlite_backend


def _refresh_columns(backend: SQLiteBackend, table_name: str):
    """Clear introspector cache and return fresh column list."""
    backend.introspector.clear_cache()
    return backend.introspector.list_columns(table_name)


class TestAlterTableAddColumn:
    """Verify ADD COLUMN via expression + introspector."""

    def test_add_column_appears_in_introspector(self, backend_with_users):
        """ADD COLUMN should be reflected by the introspector."""
        add_action = AddColumn(
            backend_with_users.dialect,
            column=ColumnDefinition("email", "TEXT"),
        )
        alter_expr = AlterTableExpression(
            backend_with_users.dialect,
            table_name="users",
            actions=[add_action],
        )
        backend_with_users.execute(*alter_expr.to_sql())

        columns = _refresh_columns(backend_with_users, "users")
        column_names = [c.name for c in columns]
        assert "email" in column_names

    def test_add_column_with_not_null(self, backend_with_users):
        """ADD COLUMN with NOT NULL constraint should be introspectable."""
        add_action = AddColumn(
            backend_with_users.dialect,
            column=ColumnDefinition(
                "status",
                "TEXT",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)],
            ),
        )
        alter_expr = AlterTableExpression(
            backend_with_users.dialect,
            table_name="users",
            actions=[add_action],
        )
        backend_with_users.execute(*alter_expr.to_sql())

        columns = _refresh_columns(backend_with_users, "users")
        status_col = next(c for c in columns if c.name == "status")
        assert status_col is not None
        assert status_col.nullable == ColumnNullable.NOT_NULL


class TestAlterTableDropColumn:
    """Verify DROP COLUMN via expression + introspector.

    SQLite 3.35.0+ supports DROP COLUMN. The test is skipped on older versions.
    """

    def test_drop_column_removed_from_introspector(self, backend_with_users):
        """DROP COLUMN should remove the column from introspector results."""
        if backend_with_users.dialect.version < (3, 35, 0):
            pytest.skip("SQLite DROP COLUMN requires 3.35.0+")

        # First add a column to drop
        add_action = AddColumn(
            backend_with_users.dialect,
            column=ColumnDefinition("temp_field", "TEXT"),
        )
        alter_add = AlterTableExpression(
            backend_with_users.dialect,
            table_name="users",
            actions=[add_action],
        )
        backend_with_users.execute(*alter_add.to_sql())

        # Verify it exists
        columns = _refresh_columns(backend_with_users, "users")
        assert "temp_field" in [c.name for c in columns]

        # Now drop it
        drop_action = DropColumn(
            backend_with_users.dialect,
            column_name="temp_field",
        )
        alter_drop = AlterTableExpression(
            backend_with_users.dialect,
            table_name="users",
            actions=[drop_action],
        )
        backend_with_users.execute(*alter_drop.to_sql())

        # Verify it's gone (refresh cache after structural change)
        columns = _refresh_columns(backend_with_users, "users")
        assert "temp_field" not in [c.name for c in columns]


class TestAlterTableRenameColumn:
    """Verify RENAME COLUMN via expression + introspector."""

    def test_rename_column_reflected_in_introspector(self, backend_with_users):
        """RENAME COLUMN should change the column name in introspector results."""
        rename_action = RenameColumn(
            backend_with_users.dialect,
            old_name="name",
            new_name="full_name",
        )
        alter_expr = AlterTableExpression(
            backend_with_users.dialect,
            table_name="users",
            actions=[rename_action],
        )
        backend_with_users.execute(*alter_expr.to_sql())

        columns = _refresh_columns(backend_with_users, "users")
        column_names = [c.name for c in columns]
        assert "full_name" in column_names
        assert "name" not in column_names


class TestAlterTableAddConstraint:
    """Verify ADD CONSTRAINT via expression + behavioral check.

    SQLite dialect's supports_add_constraint() depends on version.
    We skip if the dialect reports it as unsupported.
    """

    def test_add_unique_constraint_enforces_uniqueness(self, backend_with_users):
        """ADD CONSTRAINT UNIQUE should prevent duplicate values."""
        if not backend_with_users.dialect.supports_add_constraint():
            pytest.skip("SQLite dialect does not support ALTER TABLE ADD CONSTRAINT")

        # Add an email column
        add_action = AddColumn(
            backend_with_users.dialect,
            column=ColumnDefinition("email", "TEXT"),
        )
        alter_add = AlterTableExpression(
            backend_with_users.dialect,
            table_name="users",
            actions=[add_action],
        )
        backend_with_users.execute(*alter_add.to_sql())

        # Insert initial data
        backend_with_users.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            ("Alice", "alice@example.com"),
        )

        # Add UNIQUE constraint
        add_constraint = AddTableConstraint(
            backend_with_users.dialect,
            constraint=TableConstraint(
                constraint_type=TableConstraintType.UNIQUE,
                columns=["email"],
            ),
        )
        alter_constraint = AlterTableExpression(
            backend_with_users.dialect,
            table_name="users",
            actions=[add_constraint],
        )
        backend_with_users.execute(*alter_constraint.to_sql())

        # Attempting to insert duplicate should fail
        with pytest.raises(Exception):  # noqa: B017
            backend_with_users.execute(
                "INSERT INTO users (name, email) VALUES (?, ?)",
                ("Bob", "alice@example.com"),
            )


class TestActionDialectBinding:
    """Verify that AlterTableAction subclasses properly bind dialect at construction."""

    def test_action_has_dialect_after_construction(self, sqlite_backend):
        """Action should have its dialect accessible after construction."""
        action = AddColumn(
            sqlite_backend.dialect,
            column=ColumnDefinition("x", "INTEGER"),
        )
        assert action.dialect is sqlite_backend.dialect

    def test_action_to_sql_works_directly(self, sqlite_backend):
        """Action.to_sql() should work without wrapping in AlterTableExpression."""
        action = AddColumn(
            sqlite_backend.dialect,
            column=ColumnDefinition("x", "INTEGER"),
        )
        sql, params = action.to_sql()
        assert "ADD COLUMN" in sql
        assert '"x"' in sql

    def test_action_isinstance_tosql_protocol(self, sqlite_backend):
        """Action should satisfy ToSQLProtocol."""
        from rhosocial.activerecord.backend.expression.bases import ToSQLProtocol

        action = AddColumn(
            sqlite_backend.dialect,
            column=ColumnDefinition("x", "INTEGER"),
        )
        assert isinstance(action, ToSQLProtocol)
