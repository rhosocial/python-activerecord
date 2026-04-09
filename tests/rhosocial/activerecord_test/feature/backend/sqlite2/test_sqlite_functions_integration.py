# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_functions_integration.py
"""
Integration tests for SQLite math and JSON functions.

These tests execute SQL functions against an actual SQLite database
and verify the results match expected values.
"""
import pytest
from rhosocial.activerecord.backend.expression import Column, Literal, FunctionCall, QueryExpression
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend


@pytest.fixture
def sqlite_backend_with_data():
    """Provides a SQLiteBackend connected to an in-memory database with test data."""
    backend = SQLiteBackend(database=":memory:")
    backend.connect()
    dialect = backend.dialect

    # Create a test table
    backend.execute(
        "CREATE TABLE test_data (id INTEGER PRIMARY KEY, value REAL, text TEXT, json_data TEXT)",
        (),
        options=ExecutionOptions(stmt_type=StatementType.DDL)
    )

    # Insert test data
    backend.execute(
        "INSERT INTO test_data (value, text, json_data) VALUES (?, ?, ?)",
        (16.0, "hello", '{"a": 1, "b": 2}'),
        options=ExecutionOptions(stmt_type=StatementType.DML)
    )
    backend.execute(
        "INSERT INTO test_data (value, text, json_data) VALUES (?, ?, ?)",
        (25.0, "world", '{"a": 3, "b": 4}'),
        options=ExecutionOptions(stmt_type=StatementType.DML)
    )
    backend.execute(
        "INSERT INTO test_data (value, text, json_data) VALUES (?, ?, ?)",
        (100.0, "test", '[1, 2, 3]'),
        options=ExecutionOptions(stmt_type=StatementType.DML)
    )

    yield backend, dialect
    backend.disconnect()


class TestMathFunctionsIntegration:
    """Integration tests for SQLite math functions with actual execution."""

    def test_sqrt_execution(self, sqlite_backend_with_data):
        """Test SQRT function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "SQRT", Literal(dialect, 16)).as_("result")
        query = QueryExpression(dialect, select=[result])
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["result"] == 4.0

    def test_round_sql_execution(self, sqlite_backend_with_data):
        """Test ROUND function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "ROUND", Column(dialect, "value"), Literal(dialect, 1)).as_("rounded")
        query = QueryExpression(dialect, select=[result, Column(dialect, "value")], from_="test_data")
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["rounded"] == 16.0

    def test_pow_execution(self, sqlite_backend_with_data):
        """Test POW function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "POW", Column(dialect, "value"), Literal(dialect, 2)).as_("powered")
        query = QueryExpression(dialect, select=[result, Column(dialect, "value")], from_="test_data")
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["powered"] == 256.0
        assert query_result.data[1]["powered"] == 625.0

    def test_power_execution(self, sqlite_backend_with_data):
        """Test POWER function execution (alias for POW)."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "POWER", Literal(dialect, 2), Literal(dialect, 3)).as_("result")
        query = QueryExpression(dialect, select=[result])
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["result"] == 8.0

    def test_mod_execution(self, sqlite_backend_with_data):
        """Test MOD function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "MOD", Column(dialect, "value"), Literal(dialect, 10)).as_("modded")
        query = QueryExpression(dialect, select=[result, Column(dialect, "value")], from_="test_data")
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["modded"] == 6.0
        assert query_result.data[1]["modded"] == 5.0

    def test_ceil_execution(self, sqlite_backend_with_data):
        """Test CEIL function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "CEIL", Literal(dialect, 3.14)).as_("result")
        query = QueryExpression(dialect, select=[result])
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["result"] == 4.0

    def test_floor_execution(self, sqlite_backend_with_data):
        """Test FLOOR function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "FLOOR", Literal(dialect, 3.14)).as_("result")
        query = QueryExpression(dialect, select=[result])
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["result"] == 3.0

    def test_trunc_execution(self, sqlite_backend_with_data):
        """Test TRUNC function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "TRUNC", Literal(dialect, 3.14)).as_("result")
        query = QueryExpression(dialect, select=[result])
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["result"] == 3.0

    def test_max_sql_execution(self, sqlite_backend_with_data):
        """Test MAX function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "MAX", Literal(dialect, 1), Literal(dialect, 5), Literal(dialect, 3), Literal(dialect, 9), Literal(dialect, 2)).as_("result")
        query = QueryExpression(dialect, select=[result])
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["result"] == 9

    def test_min_sql_execution(self, sqlite_backend_with_data):
        """Test MIN function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "MIN", Literal(dialect, 1), Literal(dialect, 5), Literal(dialect, 3), Literal(dialect, 9), Literal(dialect, 2)).as_("result")
        query = QueryExpression(dialect, select=[result])
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["result"] == 1

    def test_avg_execution(self, sqlite_backend_with_data):
        """Test AVG function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "AVG", Column(dialect, "value")).as_("avg_value")
        query = QueryExpression(dialect, select=[result], from_="test_data")
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["avg_value"] == 47.0


class TestJSONFunctionsIntegration:
    """Integration tests for SQLite JSON functions with actual execution."""

    def test_json_function_execution(self, sqlite_backend_with_data):
        """Test JSON function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "JSON", Literal(dialect, '{"a": 1}')).as_("result")
        query = QueryExpression(dialect, select=[result])
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["result"] == '{"a":1}'

    def test_json_array_execution(self, sqlite_backend_with_data):
        """Test JSON_ARRAY function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "JSON_ARRAY", Literal(dialect, 1), Literal(dialect, 2), Literal(dialect, 3)).as_("result")
        query = QueryExpression(dialect, select=[result])
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["result"] == '[1,2,3]'

    def test_json_object_execution(self, sqlite_backend_with_data):
        """Test JSON_OBJECT function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "JSON_OBJECT", Literal(dialect, "a"), Literal(dialect, 1), Literal(dialect, "b"), Literal(dialect, 2)).as_("result")
        query = QueryExpression(dialect, select=[result])
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["result"] == '{"a":1,"b":2}'

    def test_json_extract_execution(self, sqlite_backend_with_data):
        """Test JSON_EXTRACT function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "JSON_EXTRACT", Column(dialect, "json_data"), Literal(dialect, "$.a")).as_("extracted")
        query = QueryExpression(dialect, select=[result], from_="test_data")
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["extracted"] == 1
        assert query_result.data[1]["extracted"] == 3

    def test_json_type_execution(self, sqlite_backend_with_data):
        """Test JSON_TYPE function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "JSON_TYPE", Column(dialect, "json_data"), Literal(dialect, "$.a")).as_("result")
        query = QueryExpression(dialect, select=[result], from_="test_data")
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["result"] == 'integer'

    def test_json_valid_execution(self, sqlite_backend_with_data):
        """Test JSON_VALID function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "JSON_VALID", Column(dialect, "json_data")).as_("valid")
        query = QueryExpression(dialect, select=[result, Column(dialect, "json_data")], from_="test_data")
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["valid"] == 1
        assert query_result.data[2]["valid"] == 1

    def test_json_quote_execution(self, sqlite_backend_with_data):
        """Test JSON_QUOTE function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "JSON_QUOTE", Literal(dialect, "hello")).as_("result")
        query = QueryExpression(dialect, select=[result])
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["result"] == '"hello"'

    def test_json_remove_execution(self, sqlite_backend_with_data):
        """Test JSON_REMOVE function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "JSON_REMOVE", Column(dialect, "json_data"), Literal(dialect, "$.a")).as_("removed")
        query = QueryExpression(dialect, select=[result], from_="test_data")
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["removed"] == '{"b":2}'

    def test_json_set_execution(self, sqlite_backend_with_data):
        """Test JSON_SET function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "JSON_SET", Column(dialect, "json_data"), Literal(dialect, "$.c"), Literal(dialect, 3)).as_("result")
        query = QueryExpression(dialect, select=[result], from_="test_data")
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["result"] == '{"a":1,"b":2,"c":3}'

    def test_json_insert_execution(self, sqlite_backend_with_data):
        """Test JSON_INSERT function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "JSON_INSERT", Column(dialect, "json_data"), Literal(dialect, "$.c"), Literal(dialect, 3)).as_("result")
        query = QueryExpression(dialect, select=[result], from_="test_data")
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["result"] == '{"a":1,"b":2,"c":3}'

    def test_json_replace_execution(self, sqlite_backend_with_data):
        """Test JSON_REPLACE function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "JSON_REPLACE", Column(dialect, "json_data"), Literal(dialect, "$.a"), Literal(dialect, 10)).as_("result")
        query = QueryExpression(dialect, select=[result], from_="test_data")
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["result"] == '{"a":10,"b":2}'

    def test_json_patch_execution(self, sqlite_backend_with_data):
        """Test JSON_PATCH function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "JSON_PATCH", Column(dialect, "json_data"), Literal(dialect, '{"a": 10}')).as_("result")
        query = QueryExpression(dialect, select=[result], from_="test_data")
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["result"] == '{"a":10,"b":2}'

    def test_json_array_length_execution(self, sqlite_backend_with_data):
        """Test JSON_ARRAY_LENGTH function execution."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "JSON_ARRAY_LENGTH", Column(dialect, "json_data")).as_("length")
        query = QueryExpression(dialect, select=[result], from_="test_data")
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["length"] == 0  # object has 0 array elements
        assert query_result.data[2]["length"] == 3  # array has length 3

    def test_json_object_retrieve_execution(self, sqlite_backend_with_data):
        """Test json_object_retrieve function execution (uses JSON_EXTRACT internally)."""
        backend, dialect = sqlite_backend_with_data

        result = FunctionCall(dialect, "JSON_EXTRACT", Column(dialect, "json_data"), Literal(dialect, "$.a")).as_("retrieved")
        query = QueryExpression(dialect, select=[result], from_="test_data")
        sql, params = query.to_sql()

        query_result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert query_result.data[0]["retrieved"] == 1
        assert query_result.data[1]["retrieved"] == 3
