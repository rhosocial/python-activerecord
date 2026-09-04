# tests/rhosocial/activerecord_test/feature/backend/dml/test_returning_async.py
"""Async twin of test_returning.py: sync mixin unit tests kept sync; backend integration tests async."""
import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock

from rhosocial.activerecord.backend.base.returning import ReturningClauseMixin
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.expression import ReturningClause, Column, Literal


# --- Unit tests for ReturningClauseMixin (sync API under test, kept sync) ---


class TestAsyncReturningClauseMixin:
    @pytest.fixture
    def mixin_instance(self):
        """Creates an instance of a class that uses ReturningClauseMixin for testing."""

        class TestClass(ReturningClauseMixin):
            def __init__(self):
                self.dialect = DummyDialect()

        return TestClass()

    def test_process_returning_clause_with_none(self, mixin_instance):
        assert mixin_instance._process_returning_clause(None) is None

    def test_process_returning_clause_with_false(self, mixin_instance):
        assert mixin_instance._process_returning_clause(False) is None

    def test_process_returning_clause_with_true(self, mixin_instance):
        returning_clause = mixin_instance._process_returning_clause(True)
        assert isinstance(returning_clause, ReturningClause)
        assert len(returning_clause.expressions) == 1
        assert isinstance(returning_clause.expressions[0], Literal)
        assert returning_clause.expressions[0].value == "*"

    def test_process_returning_clause_with_list_of_strings(self, mixin_instance):
        returning_clause = mixin_instance._process_returning_clause(["id", "name"])
        assert isinstance(returning_clause, ReturningClause)
        assert len(returning_clause.expressions) == 2
        assert isinstance(returning_clause.expressions[0], Column)
        assert returning_clause.expressions[0].name == "id"
        assert isinstance(returning_clause.expressions[1], Column)
        assert returning_clause.expressions[1].name == "name"

    def test_process_returning_clause_with_list_of_expressions(self, mixin_instance):
        expressions = [Column(mixin_instance.dialect, "id"), Literal(mixin_instance.dialect, "test")]
        returning_clause = mixin_instance._process_returning_clause(expressions)
        assert isinstance(returning_clause, ReturningClause)
        assert returning_clause.expressions == expressions

    def test_process_returning_clause_with_returning_clause_object(self, mixin_instance):
        original_clause = ReturningClause(mixin_instance.dialect, expressions=[Column(mixin_instance.dialect, "id")])
        processed_clause = mixin_instance._process_returning_clause(original_clause)
        assert processed_clause is original_clause

    def test_process_returning_clause_with_invalid_type(self, mixin_instance):
        with pytest.raises(ValueError, match="Unsupported returning type"):
            mixin_instance._process_returning_clause(123)

    def test_prepare_returning_clause(self, mixin_instance):
        sql = "INSERT INTO users (name) VALUES ('test')"
        returning_clause = ReturningClause(mixin_instance.dialect, expressions=[Column(mixin_instance.dialect, "id")])
        returning_clause.to_sql = MagicMock(return_value=('RETURNING "id"', ()))
        new_sql = mixin_instance._prepare_returning_clause(sql, returning_clause, StatementType.INSERT)
        assert new_sql == "INSERT INTO users (name) VALUES ('test') RETURNING \"id\""

    def test_prepare_returning_clause_with_no_clause(self, mixin_instance):
        sql = "DELETE FROM users WHERE id = 1"
        new_sql = mixin_instance._prepare_returning_clause(sql, None, StatementType.DELETE)
        assert new_sql == sql


# --- Integration tests for SQLite RETURNING functionality (async) ---


@pytest_asyncio.fixture
async def backend():
    """Provides an AsyncSQLiteBackend instance connected to an in-memory database."""
    backend = AsyncSQLiteBackend(database=":memory:")
    await backend.connect()
    await backend.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT
        )
        """,
        options=ExecutionOptions(stmt_type=StatementType.DDL),
    )
    yield backend
    await backend.disconnect()


@pytest.mark.asyncio
@patch("sqlite3.sqlite_version_info", (3, 35, 0))
async def test_returning_with_insert(backend):
    """Tests INSERT with RETURNING on a supported version (async)."""
    sql = "INSERT INTO users (name, email) VALUES (?, ?) RETURNING id, name"
    params = ("Alice", "alice@example.com")
    options = ExecutionOptions(stmt_type=StatementType.DQL)

    result = await backend.execute(sql, params, options=options)

    assert result.data is not None
    assert len(result.data) == 1
    assert result.data[0]["id"] == 1
    assert result.data[0]["name"] == "Alice"


@pytest.mark.asyncio
@patch("sqlite3.sqlite_version_info", (3, 35, 0))
async def test_returning_with_update(backend):
    """Tests UPDATE with RETURNING on a supported version (async)."""
    await backend.execute(
        "INSERT INTO users (name, email) VALUES ('Bob', 'bob@example.com')",
        options=ExecutionOptions(stmt_type=StatementType.DML),
    )

    sql = "UPDATE users SET email = ? WHERE name = ? RETURNING id, email"
    params = ("bob_new@example.com", "Bob")
    options = ExecutionOptions(stmt_type=StatementType.DQL)

    result = await backend.execute(sql, params, options=options)

    assert result.data is not None
    assert len(result.data) == 1
    assert result.data[0]["id"] == 1
    assert result.data[0]["email"] == "bob_new@example.com"


@pytest.mark.asyncio
@patch("sqlite3.sqlite_version_info", (3, 35, 0))
async def test_returning_with_delete(backend):
    """Tests DELETE with RETURNING on a supported version (async)."""
    await backend.execute(
        "INSERT INTO users (name, email) VALUES ('Charlie', 'charlie@example.com')",
        options=ExecutionOptions(stmt_type=StatementType.DML),
    )

    sql = "DELETE FROM users WHERE name = ? RETURNING id, name"
    params = ("Charlie",)
    options = ExecutionOptions(stmt_type=StatementType.DQL)

    result = await backend.execute(sql, params, options=options)

    assert result.data is not None
    assert len(result.data) == 1
    assert result.data[0]["id"] == 1
    assert result.data[0]["name"] == "Charlie"
