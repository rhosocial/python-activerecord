# tests/rhosocial/activerecord_test/feature/backend/introspection/test_sqlite_3_53_integration_async.py
"""Async twin of test_sqlite_3_53_integration.py for SQLite 3.53.0 dialect capability detection."""

import pytest

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.expression import SQLiteReindexExpression
from rhosocial.activerecord.backend.impl.sqlite.functions import (
    json_array_insert,
    jsonb_array_insert,
)
from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

from rhosocial.activerecord.backend.dialect.protocols import ConstraintSupport
from rhosocial.activerecord.backend.impl.sqlite.protocols import SQLiteReindexSupport


def has_sqlite_353_capabilities():
    """Check if current SQLite has 3.53.0+ capabilities (sync dialect detection)."""
    test_backend = SQLiteBackend(database=":memory:")
    test_backend.connect()
    test_backend.introspect_and_adapt()
    dialect = test_backend._dialect
    has_353 = (
        dialect.supports_add_constraint()
        and dialect.supports_drop_constraint()
        and dialect.supports_reindex_expressions()
    )
    test_backend.disconnect()
    return has_353


pytestmark = pytest.mark.skipif(not has_sqlite_353_capabilities(), reason="SQLite 3.53.0+ capabilities not available")


class TestAsyncSQLite353DialectCapabilities:
    """Tests verifying dialect correctly reports SQLite 3.53.0+ capabilities."""

    @pytest.mark.requires_protocol((ConstraintSupport, "supports_add_constraint"))
    @pytest.mark.asyncio
    async def test_supports_add_constraint_true_on_353(self, async_sqlite_memory_backend):
        """Test that supports_add_constraint returns True on SQLite 3.53+."""
        await async_sqlite_memory_backend.introspect_and_adapt()

        dialect = async_sqlite_memory_backend._dialect
        assert dialect.supports_add_constraint() is True

    @pytest.mark.requires_protocol((ConstraintSupport, "supports_drop_constraint"))
    @pytest.mark.asyncio
    async def test_supports_drop_constraint_true_on_353(self, async_sqlite_memory_backend):
        """Test that supports_drop_constraint returns True on SQLite 3.53+."""
        await async_sqlite_memory_backend.introspect_and_adapt()

        dialect = async_sqlite_memory_backend._dialect
        assert dialect.supports_drop_constraint() is True

    @pytest.mark.requires_protocol((SQLiteReindexSupport, "supports_reindex_expressions"))
    @pytest.mark.asyncio
    async def test_supports_reindex_expressions_true_on_353(self, async_sqlite_memory_backend):
        """Test that supports_reindex_expressions returns True on SQLite 3.53+."""
        await async_sqlite_memory_backend.introspect_and_adapt()

        dialect = async_sqlite_memory_backend._dialect
        assert dialect.supports_reindex_expressions() is True

    @pytest.mark.asyncio
    async def test_json_array_insert_function_available(self, async_sqlite_memory_backend):
        """Test that json_array_insert function is marked as available."""
        await async_sqlite_memory_backend.introspect_and_adapt()

        dialect = async_sqlite_memory_backend._dialect
        funcs = dialect.supports_functions()
        assert funcs.get("json_array_insert") is True

    @pytest.mark.asyncio
    async def test_jsonb_array_insert_function_available(self, async_sqlite_memory_backend):
        """Test that jsonb_array_insert function is marked as available."""
        await async_sqlite_memory_backend.introspect_and_adapt()

        dialect = async_sqlite_memory_backend._dialect
        funcs = dialect.supports_functions()
        assert funcs.get("jsonb_array_insert") is True


class TestAsyncSQLite353ExpressionSQLGeneration:
    """Tests for SQL generation of SQLite 3.53.0+ expressions."""

    @pytest.mark.requires_protocol((SQLiteReindexSupport, "supports_reindex_expressions"))
    @pytest.mark.asyncio
    async def test_reindex_expressions_sql_generation(self, async_sqlite_memory_backend):
        """Test that REINDEX EXPRESSIONS SQL is generated correctly."""
        await async_sqlite_memory_backend.introspect_and_adapt()

        dialect = async_sqlite_memory_backend._dialect
        reindex_expr = SQLiteReindexExpression(dialect, expressions=True)
        sql, params = reindex_expr.to_sql()

        assert sql == "REINDEX EXPRESSIONS"
        assert params == ()

    @pytest.mark.asyncio
    async def test_json_array_insert_sql_generation(self, async_sqlite_memory_backend):
        """Test that json_array_insert SQL is generated correctly."""
        await async_sqlite_memory_backend.introspect_and_adapt()

        dialect = async_sqlite_memory_backend._dialect
        col_data = Column(dialect, "data", table="test_table")
        json_expr = json_array_insert(dialect, col_data, Literal(dialect, "new"), position=0)

        sql, params = json_expr.to_sql()
        assert "JSON_ARRAY_INSERT" in sql

    @pytest.mark.asyncio
    async def test_jsonb_array_insert_sql_generation(self, async_sqlite_memory_backend):
        """Test that jsonb_array_insert SQL is generated correctly."""
        await async_sqlite_memory_backend.introspect_and_adapt()

        dialect = async_sqlite_memory_backend._dialect
        col_data = Column(dialect, "data", table="test_table")
        json_expr = jsonb_array_insert(dialect, col_data, Literal(dialect, "new"), position=1)

        sql, params = json_expr.to_sql()
        assert "JSONB_ARRAY_INSERT" in sql


class TestAsyncSQLite353ReindexExecution:
    """Integration tests for REINDEX EXPRESSIONS execution."""

    @pytest.mark.requires_protocol((SQLiteReindexSupport, "supports_reindex_expressions"))
    @pytest.mark.asyncio
    async def test_reindex_expressions_executes(self, async_sqlite_memory_backend):
        """Test that REINDEX EXPRESSIONS can be executed."""
        await async_sqlite_memory_backend.introspect_and_adapt()

        dialect = async_sqlite_memory_backend._dialect

        await async_sqlite_memory_backend.executescript("""
            CREATE TABLE test_expr_idx (
                id INTEGER PRIMARY KEY,
                value TEXT
            );
            CREATE INDEX idx_lower_value ON test_expr_idx(LOWER(value));
        """)

        reindex_expr = SQLiteReindexExpression(dialect, expressions=True)
        sql, params = reindex_expr.to_sql()

        await async_sqlite_memory_backend.execute(sql, params)

    @pytest.mark.requires_protocol((SQLiteReindexSupport, "supports_reindex_expressions"))
    @pytest.mark.asyncio
    async def test_reindex_expressions_on_empty_db(self, async_sqlite_memory_backend):
        """Test REINDEX EXPRESSIONS on database without expression indexes."""
        await async_sqlite_memory_backend.introspect_and_adapt()

        dialect = async_sqlite_memory_backend._dialect

        await async_sqlite_memory_backend.executescript("""
            CREATE TABLE simple_table (
                id INTEGER PRIMARY KEY,
                name TEXT
            );
        """)

        reindex_expr = SQLiteReindexExpression(dialect, expressions=True)
        sql, params = reindex_expr.to_sql()

        await async_sqlite_memory_backend.execute(sql, params)


class TestAsyncSQLite353JsonFunctionsSQL:
    """Tests for json_array_insert/jsonb_array_insert SQL generation."""

    @pytest.mark.asyncio
    async def test_json_array_insert_sql_and_params(self, async_sqlite_memory_backend):
        """Test that json_array_insert generates correct SQL and parameters."""
        await async_sqlite_memory_backend.introspect_and_adapt()

        dialect = async_sqlite_memory_backend._dialect

        col_data = Column(dialect, "data", table="test_json")
        json_expr = json_array_insert(dialect, col_data, Literal(dialect, 0), position=0)
        sql, params = json_expr.to_sql()

        assert "JSON_ARRAY_INSERT" in sql
        assert len(params) == 2

    @pytest.mark.asyncio
    async def test_jsonb_array_insert_sql_and_params(self, async_sqlite_memory_backend):
        """Test that jsonb_array_insert generates correct SQL and parameters."""
        await async_sqlite_memory_backend.introspect_and_adapt()

        dialect = async_sqlite_memory_backend._dialect

        col_data = Column(dialect, "data", table="test_jsonb")
        json_expr = jsonb_array_insert(dialect, col_data, Literal(dialect, 100), position=1)
        sql, params = json_expr.to_sql()

        assert "JSONB_ARRAY_INSERT" in sql
        assert len(params) == 2


class TestAsyncSQLite353JsonFunctionsExecution:
    """Integration tests for json_array_insert/jsonb_array_insert execution."""

    @pytest.mark.requires_functions("json_array_insert")
    @pytest.mark.asyncio
    async def test_json_array_insert_executes(self, async_sqlite_memory_backend):
        """Test that json_array_insert executes and returns expected result."""
        await async_sqlite_memory_backend.introspect_and_adapt()

        dialect = async_sqlite_memory_backend._dialect
        dql_options = ExecutionOptions(stmt_type=StatementType.DQL)

        await async_sqlite_memory_backend.executescript("""
            CREATE TABLE test_json (
                id INTEGER PRIMARY KEY,
                data TEXT
            );
            INSERT INTO test_json (data) VALUES ('[1, 2, 3]');
        """)

        col_data = Column(dialect, "data", table="test_json")
        json_expr = json_array_insert(dialect, col_data, Literal(dialect, 0), position=0)

        from rhosocial.activerecord.backend.expression import QueryExpression, TableExpression

        query = QueryExpression(
            dialect=dialect,
            select=[
                json_expr.as_("modified"),
            ],
            from_=TableExpression(dialect, "test_json"),
        )

        sql, params = query.to_sql()
        result = await async_sqlite_memory_backend.execute(sql, params, options=dql_options)

        assert result.data is not None
        assert len(result.data) == 1
        modified_json = result.data[0]["modified"]
        assert "0" in modified_json

    @pytest.mark.requires_functions("jsonb_array_insert")
    @pytest.mark.asyncio
    async def test_jsonb_array_insert_executes(self, async_sqlite_memory_backend):
        """Test that jsonb_array_insert executes and returns expected result."""
        await async_sqlite_memory_backend.introspect_and_adapt()

        dialect = async_sqlite_memory_backend._dialect
        dql_options = ExecutionOptions(stmt_type=StatementType.DQL)

        await async_sqlite_memory_backend.executescript("""
            CREATE TABLE test_jsonb (
                id INTEGER PRIMARY KEY,
                data TEXT
            );
            INSERT INTO test_jsonb (data) VALUES ('[1, 2, 3]');
        """)

        col_data = Column(dialect, "data", table="test_jsonb")
        json_expr = jsonb_array_insert(dialect, col_data, Literal(dialect, "new_value"), position=1)

        from rhosocial.activerecord.backend.expression import QueryExpression, TableExpression

        query = QueryExpression(
            dialect=dialect,
            select=[
                json_expr.as_("modified"),
            ],
            from_=TableExpression(dialect, "test_jsonb"),
        )

        sql, params = query.to_sql()
        result = await async_sqlite_memory_backend.execute(sql, params, options=dql_options)

        assert result.data is not None
        assert len(result.data) == 1


class TestAsyncSQLite353AlterTableConstraint:
    """Integration tests for ALTER TABLE ADD/DROP CONSTRAINT."""

    @pytest.mark.requires_protocol((ConstraintSupport, "supports_add_constraint"))
    @pytest.mark.asyncio
    async def test_alter_table_add_check_constraint(self, async_sqlite_memory_backend):
        """Test ALTER TABLE ADD CONSTRAINT with CHECK."""
        await async_sqlite_memory_backend.introspect_and_adapt()

        await async_sqlite_memory_backend.executescript("""
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                name TEXT,
                price INTEGER
            );
            INSERT INTO products (name, price) VALUES ('Apple', 100);
        """)

        await async_sqlite_memory_backend.execute(
            "ALTER TABLE products ADD CONSTRAINT chk_price_positive CHECK (price >= 0)", ()
        )

        result = await async_sqlite_memory_backend.execute(
            "INSERT INTO products (name, price) VALUES ('Banana', 50)", ()
        )
        assert result.affected_rows == 1

    @pytest.mark.requires_protocol((ConstraintSupport, "supports_drop_constraint"))
    @pytest.mark.asyncio
    async def test_alter_table_drop_constraint(self, async_sqlite_memory_backend):
        """Test ALTER TABLE DROP CONSTRAINT."""
        await async_sqlite_memory_backend.introspect_and_adapt()

        await async_sqlite_memory_backend.executescript("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                status TEXT,
                CONSTRAINT chk_status CHECK (status IN ('pending', 'completed'))
            );
        """)

        await async_sqlite_memory_backend.execute("ALTER TABLE orders DROP CONSTRAINT chk_status", ())

        result = await async_sqlite_memory_backend.execute(
            "INSERT INTO orders (status) VALUES ('cancelled')", ()
        )
        assert result.affected_rows == 1
