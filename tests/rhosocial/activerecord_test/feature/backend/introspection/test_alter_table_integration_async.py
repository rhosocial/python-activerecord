# tests/rhosocial/activerecord_test/feature/backend/introspection/test_alter_table_integration_async.py
"""Async twin of test_alter_table_integration.py for ALTER TABLE operations via the expression system."""

import pytest
import pytest_asyncio

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
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.introspection.types import ColumnNullable
from rhosocial.activerecord.backend.impl.sqlite.expression.types import SQLiteIntegerType, SQLiteTextType


@pytest_asyncio.fixture
async def backend_with_users(async_sqlite_memory_backend):
    """Create a backend with a simple 'users' table for ALTER TABLE tests."""
    create_expr = CreateTableExpression(
        dialect=async_sqlite_memory_backend.dialect,
        table="users",
        columns=[
            ColumnDefinition(
                "id",
                SQLiteIntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)],
            ),
            ColumnDefinition("name", SQLiteTextType()),
        ],
    )
    await async_sqlite_memory_backend.execute(*create_expr.to_sql())
    return async_sqlite_memory_backend


async def _refresh_columns(backend, table_name):
    """Clear introspector cache and return fresh column list."""
    backend.introspector.clear_cache()
    return await backend.introspector.list_columns(table_name)


class TestAsyncAlterTableAddColumn:
    """Verify ADD COLUMN via expression + introspector."""

    @pytest.mark.asyncio
    async def test_add_column_appears_in_introspector(self, backend_with_users):
        """ADD COLUMN should be reflected by the introspector."""
        add_action = AddColumn(
            backend_with_users.dialect,
            column=ColumnDefinition("email", SQLiteTextType()),
        )
        alter_expr = AlterTableExpression(
            backend_with_users.dialect,
            table="users",
            actions=[add_action],
        )
        await backend_with_users.execute(*alter_expr.to_sql())

        columns = await _refresh_columns(backend_with_users, "users")
        column_names = [c.name for c in columns]
        assert "email" in column_names

    @pytest.mark.asyncio
    async def test_add_column_with_not_null(self, backend_with_users):
        """ADD COLUMN with NOT NULL constraint should be introspectable."""
        add_action = AddColumn(
            backend_with_users.dialect,
            column=ColumnDefinition(
                "status",
                SQLiteTextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)],
            ),
        )
        alter_expr = AlterTableExpression(
            backend_with_users.dialect,
            table="users",
            actions=[add_action],
        )
        await backend_with_users.execute(*alter_expr.to_sql())

        columns = await _refresh_columns(backend_with_users, "users")
        status_col = next(c for c in columns if c.name == "status")
        assert status_col is not None
        assert status_col.nullable == ColumnNullable.NOT_NULL


class TestAsyncAlterTableDropColumn:
    """Verify DROP COLUMN via expression + introspector (requires SQLite 3.35.0+)."""

    @pytest.mark.asyncio
    async def test_drop_column_removed_from_introspector(self, backend_with_users):
        """DROP COLUMN should remove the column from introspector results."""
        if backend_with_users.dialect.version < (3, 35, 0):
            pytest.skip("SQLite DROP COLUMN requires 3.35.0+")

        add_action = AddColumn(
            backend_with_users.dialect,
            column=ColumnDefinition("temp_field", SQLiteTextType()),
        )
        alter_add = AlterTableExpression(
            backend_with_users.dialect,
            table="users",
            actions=[add_action],
        )
        await backend_with_users.execute(*alter_add.to_sql())

        columns = await _refresh_columns(backend_with_users, "users")
        assert "temp_field" in [c.name for c in columns]

        drop_action = DropColumn(
            backend_with_users.dialect,
            column_name="temp_field",
        )
        alter_drop = AlterTableExpression(
            backend_with_users.dialect,
            table="users",
            actions=[drop_action],
        )
        await backend_with_users.execute(*alter_drop.to_sql())

        columns = await _refresh_columns(backend_with_users, "users")
        assert "temp_field" not in [c.name for c in columns]


class TestAsyncAlterTableRenameColumn:
    """Verify RENAME COLUMN via expression + introspector."""

    @pytest.mark.asyncio
    async def test_rename_column_reflected_in_introspector(self, backend_with_users):
        """RENAME COLUMN should change the column name in introspector results."""
        rename_action = RenameColumn(
            backend_with_users.dialect,
            old_name="name",
            new_name="full_name",
        )
        alter_expr = AlterTableExpression(
            backend_with_users.dialect,
            table="users",
            actions=[rename_action],
        )
        await backend_with_users.execute(*alter_expr.to_sql())

        columns = await _refresh_columns(backend_with_users, "users")
        column_names = [c.name for c in columns]
        assert "full_name" in column_names
        assert "name" not in column_names


class TestAsyncAlterTableAddConstraint:
    """Verify ADD CONSTRAINT via expression + behavioral check (version dependent)."""

    @pytest.mark.asyncio
    async def test_add_check_constraint_enforces_non_null(self, backend_with_users):
        """ADD CONSTRAINT CHECK should prevent NULL values."""
        if not backend_with_users.dialect.supports_add_constraint():
            pytest.skip("SQLite dialect does not support ALTER TABLE ADD CONSTRAINT")

        from rhosocial.activerecord.backend.expression import Column

        add_action = AddColumn(
            backend_with_users.dialect,
            column=ColumnDefinition("email", SQLiteTextType()),
        )
        alter_add = AlterTableExpression(
            backend_with_users.dialect,
            table="users",
            actions=[add_action],
        )
        await backend_with_users.execute(*alter_add.to_sql())

        await backend_with_users.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            ("Alice", "alice@example.com"),
        )

        add_constraint = AddTableConstraint(
            backend_with_users.dialect,
            constraint=TableConstraint(
                constraint_type=TableConstraintType.CHECK,
                check_condition=Column(
                    backend_with_users.dialect, "email"
                ).is_not_null(),
            ),
        )
        alter_constraint = AlterTableExpression(
            backend_with_users.dialect,
            table="users",
            actions=[add_constraint],
        )
        await backend_with_users.execute(*alter_constraint.to_sql())

        with pytest.raises(Exception):  # noqa: B017
            await backend_with_users.execute(
                "INSERT INTO users (name, email) VALUES (?, ?)",
                ("Bob", None),
            )


class TestAsyncSQLiteIfExistsGuard:
    """Verify SQLite rejects the unsupported IF [NOT] EXISTS qualifiers on ALTER TABLE."""

    @pytest.mark.asyncio
    async def test_sqlite_rejects_add_column_if_not_exists(self, async_sqlite_memory_backend):
        """ADD COLUMN IF NOT EXISTS must raise on SQLite."""
        action = AddColumn(
            async_sqlite_memory_backend.dialect,
            column=ColumnDefinition("email", SQLiteTextType()),
            if_not_exists=True,
        )
        with pytest.raises(UnsupportedFeatureError):
            action.to_sql()

    @pytest.mark.asyncio
    async def test_sqlite_rejects_drop_column_if_exists(self, async_sqlite_memory_backend):
        """DROP COLUMN IF EXISTS must raise on SQLite."""
        action = DropColumn(
            async_sqlite_memory_backend.dialect,
            column_name="email",
            if_exists=True,
        )
        with pytest.raises(UnsupportedFeatureError):
            action.to_sql()

    @pytest.mark.asyncio
    async def test_sqlite_allows_bare_add_and_drop(self, async_sqlite_memory_backend):
        """Bare ADD/DROP COLUMN (no qualifier) must still work on SQLite."""
        add_action = AddColumn(
            async_sqlite_memory_backend.dialect,
            column=ColumnDefinition("email", SQLiteTextType()),
        )
        add_sql, _ = add_action.to_sql()
        assert "IF NOT EXISTS" not in add_sql

        drop_action = DropColumn(async_sqlite_memory_backend.dialect, column_name="email")
        drop_sql, _ = drop_action.to_sql()
        assert "IF EXISTS" not in drop_sql


class TestAsyncActionDialectBinding:
    """Verify that AlterTableAction subclasses properly bind dialect at construction."""

    @pytest.mark.asyncio
    async def test_action_has_dialect_after_construction(self, async_sqlite_memory_backend):
        """Action should have its dialect accessible after construction."""
        action = AddColumn(
            async_sqlite_memory_backend.dialect,
            column=ColumnDefinition("x", SQLiteIntegerType()),
        )
        assert action.dialect is async_sqlite_memory_backend.dialect

    @pytest.mark.asyncio
    async def test_action_to_sql_works_directly(self, async_sqlite_memory_backend):
        """Action.to_sql() should work without wrapping in AlterTableExpression."""
        action = AddColumn(
            async_sqlite_memory_backend.dialect,
            column=ColumnDefinition("x", SQLiteIntegerType()),
        )
        sql, params = action.to_sql()
        assert "ADD COLUMN" in sql
        assert '"x"' in sql

    @pytest.mark.asyncio
    async def test_action_isinstance_tosql_protocol(self, async_sqlite_memory_backend):
        """Action should satisfy ToSQLProtocol."""
        from rhosocial.activerecord.backend.expression.bases import ToSQLProtocol

        action = AddColumn(
            async_sqlite_memory_backend.dialect,
            column=ColumnDefinition("x", SQLiteIntegerType()),
        )
        assert isinstance(action, ToSQLProtocol)
