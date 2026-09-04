# tests/rhosocial/activerecord_test/feature/backend/query/test_explain_async.py
"""Async twin of test_explain.py: dialect-level EXPLAIN formatting stays sync; backend executions run on AsyncSQLiteBackend."""
import pytest

from rhosocial.activerecord.backend.expression.statements import ExplainType, ExplainOptions, ExplainExpression
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression.core import Literal


def test_format_explain_basic():
    """Test basic EXPLAIN SQL formatting (pure dialect/expression construction)."""
    dialect = SQLiteDialect()

    from rhosocial.activerecord.backend.expression.core import TableExpression
    from rhosocial.activerecord.backend.expression.statements import QueryExpression

    query_expr = QueryExpression(
        dialect=dialect, select=[Literal(dialect, "*")], from_=TableExpression(dialect, "users")
    )

    explain_expr = ExplainExpression(dialect, statement=query_expr)
    explain_sql, params = dialect.format_explain_statement(explain_expr)
    assert "EXPLAIN" in explain_sql
    assert "SELECT" in explain_sql
    assert "users" in explain_sql


def test_format_explain_query_plan():
    """Test EXPLAIN QUERY PLAN SQL formatting (pure dialect/expression construction)."""
    dialect = SQLiteDialect()

    from rhosocial.activerecord.backend.expression.core import TableExpression, Column
    from rhosocial.activerecord.backend.expression.statements import QueryExpression

    query_expr = QueryExpression(
        dialect=dialect,
        select=[Literal(dialect, "*")],
        from_=TableExpression(dialect, "users"),
        where=Column(dialect, "id") == Literal(dialect, 1),
    )

    options = ExplainOptions(analyze=False, type=ExplainType.QUERY_PLAN)
    explain_expr = ExplainExpression(dialect, statement=query_expr, options=options)
    explain_sql, params = dialect.format_explain_statement(explain_expr)
    assert "EXPLAIN" in explain_sql


def test_format_explain_with_complex_sql():
    """Test EXPLAIN formatting with complex SQL statements (pure dialect/expression construction)."""
    dialect = SQLiteDialect()

    from rhosocial.activerecord.backend.expression.core import TableExpression, Column, Literal
    from rhosocial.activerecord.backend.expression.statements import QueryExpression

    query_expr = QueryExpression(
        dialect=dialect,
        select=[Literal(dialect, "u.*"), Literal(dialect, "o.total")],
        from_=TableExpression(dialect, "users", alias="u"),
    )

    explain_expr = ExplainExpression(dialect, statement=query_expr)
    explain_sql, params = dialect.format_explain_statement(explain_expr)
    assert "EXPLAIN" in explain_sql

    QueryExpression(
        dialect=dialect,
        select=[Column(dialect, "user_id")],
        from_=TableExpression(dialect, "orders"),
        where=Column(dialect, "total") > Literal(dialect, 100),
    )

    main_query = QueryExpression(
        dialect=dialect,
        select=[Literal(dialect, "*")],
        from_=TableExpression(dialect, "users"),
    )

    options = ExplainOptions(type=ExplainType.QUERY_PLAN)
    explain_expr = ExplainExpression(dialect, statement=main_query, options=options)
    explain_sql, params = dialect.format_explain_statement(explain_expr)
    assert "EXPLAIN" in explain_sql


def test_format_explain_with_options():
    """Test EXPLAIN formatting with different options (pure dialect/expression construction)."""
    dialect = SQLiteDialect()

    from rhosocial.activerecord.backend.expression.core import TableExpression, Literal
    from rhosocial.activerecord.backend.expression.statements import QueryExpression, ExplainFormat

    query_expr = QueryExpression(
        dialect=dialect, select=[Literal(dialect, "*")], from_=TableExpression(dialect, "users")
    )

    for format_type in [ExplainFormat.TEXT, ExplainFormat.JSON]:
        options = ExplainOptions(format=format_type)
        explain_expr = ExplainExpression(dialect, statement=query_expr, options=options)
        explain_sql, params = dialect.format_explain_statement(explain_expr)
        assert "EXPLAIN" in explain_sql

    options = ExplainOptions(costs=False)
    explain_expr = ExplainExpression(dialect, statement=query_expr, options=options)
    explain_sql, params = dialect.format_explain_statement(explain_expr)
    assert "EXPLAIN" in explain_sql


@pytest.mark.asyncio
async def test_format_explain_integration():
    """Test EXPLAIN formatting integration with execute on AsyncSQLiteBackend."""
    from rhosocial.activerecord.backend.options import ExecutionOptions
    from rhosocial.activerecord.backend.schema import StatementType
    from rhosocial.activerecord.backend.expression.core import TableExpression, Literal, Column
    from rhosocial.activerecord.backend.expression.statements import QueryExpression, ExplainExpression, ExplainOptions
    from rhosocial.activerecord.backend.expression.statements import ExplainType as ExpType

    backend = AsyncSQLiteBackend(database=":memory:")
    try:
        await backend.connect()

        await backend.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """,
            (),
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )

        await backend.execute(
            "INSERT INTO users (name) VALUES (?), (?)",
            ("test1", "test2"),
            options=ExecutionOptions(stmt_type=StatementType.INSERT),
        )

        query_expr = QueryExpression(
            dialect=backend.dialect,
            select=[Literal(backend.dialect, "*")],
            from_=TableExpression(backend.dialect, "users"),
        )

        explain_expr = ExplainExpression(backend.dialect, statement=query_expr)
        explain_sql, params = backend.dialect.format_explain_statement(explain_expr)

        result = await backend.execute(
            explain_sql, params, options=ExecutionOptions(stmt_type=StatementType.SELECT)
        )
        assert result is not None

        query_expr = QueryExpression(
            dialect=backend.dialect,
            select=[Column(backend.dialect, "name", "u1")],
            from_=TableExpression(backend.dialect, "users", alias="u1"),
        )

        options = ExplainOptions(type=ExpType.QUERY_PLAN)
        explain_expr = ExplainExpression(backend.dialect, statement=query_expr, options=options)
        explain_sql, params = backend.dialect.format_explain_statement(explain_expr)

        result = await backend.execute(
            explain_sql, params, options=ExecutionOptions(stmt_type=StatementType.SELECT)
        )
        assert result is not None
    finally:
        await backend.disconnect()


@pytest.mark.asyncio
async def test_format_explain_with_transactions():
    """Test EXPLAIN formatting within transactions on AsyncSQLiteBackend."""
    from rhosocial.activerecord.backend.options import ExecutionOptions
    from rhosocial.activerecord.backend.schema import StatementType
    from rhosocial.activerecord.backend.expression.core import TableExpression, Literal
    from rhosocial.activerecord.backend.expression.statements import QueryExpression, ExplainExpression, ExplainOptions
    from rhosocial.activerecord.backend.expression.statements import ExplainType as ExpType

    backend = AsyncSQLiteBackend(database=":memory:")
    try:
        await backend.connect()

        async with backend.transaction():
            await backend.execute(
                """
                CREATE TABLE test (
                    id INTEGER PRIMARY KEY,
                    value TEXT
                )
            """,
                (),
                options=ExecutionOptions(stmt_type=StatementType.DDL),
            )

            await backend.execute(
                "INSERT INTO test (value) VALUES (?), (?)",
                ("test1", "test2"),
                options=ExecutionOptions(stmt_type=StatementType.INSERT),
            )

            query_expr = QueryExpression(
                dialect=backend.dialect,
                select=[Literal(backend.dialect, "*")],
                from_=TableExpression(backend.dialect, "test"),
            )

            options = ExplainOptions(type=ExpType.QUERY_PLAN)
            explain_expr = ExplainExpression(backend.dialect, statement=query_expr, options=options)
            explain_sql, params = backend.dialect.format_explain_statement(explain_expr)

            result = await backend.execute(
                explain_sql, params, options=ExecutionOptions(stmt_type=StatementType.SELECT)
            )
            assert result is not None

            agg_query = QueryExpression(
                dialect=backend.dialect,
                select=[Literal(backend.dialect, "COUNT(*) as cnt")],
                from_=TableExpression(backend.dialect, "test"),
            )

            explain_expr = ExplainExpression(backend.dialect, statement=agg_query)
            explain_sql, params = backend.dialect.format_explain_statement(explain_expr)

            result = await backend.execute(
                explain_sql, params, options=ExecutionOptions(stmt_type=StatementType.SELECT)
            )
            assert result is not None

        result = await backend.execute(
            "SELECT COUNT(*) as cnt FROM test", (), options=ExecutionOptions(stmt_type=StatementType.SELECT)
        )
        assert result is not None
    finally:
        await backend.disconnect()
