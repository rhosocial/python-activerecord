# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_explain.py
from rhosocial.activerecord.backend.dialect import ExplainType, ExplainOptions
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.config import ConnectionConfig


def test_format_explain_basic():
    """Test basic EXPLAIN SQL formatting"""
    dialect = SQLiteDialect(ConnectionConfig())

    # Test basic EXPLAIN
    sql = "SELECT * FROM users"
    explain_sql = dialect.format_explain(sql)
    assert explain_sql == "EXPLAIN SELECT * FROM users"

    # Test with explicit basic type
    options = ExplainOptions(type=ExplainType.BASIC)
    explain_sql = dialect.format_explain(sql, options)
    assert explain_sql == "EXPLAIN SELECT * FROM users"


def test_format_explain_query_plan():
    """Test EXPLAIN QUERY PLAN SQL formatting"""
    dialect = SQLiteDialect(ConnectionConfig())

    sql = "SELECT * FROM users WHERE id = 1"
    options = ExplainOptions(type=ExplainType.QUERYPLAN)
    explain_sql = dialect.format_explain(sql, options)
    assert explain_sql == "EXPLAIN QUERY PLAN SELECT * FROM users WHERE id = 1"


def test_format_explain_with_complex_sql():
    """Test EXPLAIN formatting with complex SQL statements"""
    dialect = SQLiteDialect(ConnectionConfig())

    # Test with JOIN
    sql = "SELECT u.*, o.total FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE o.total > 100"
    explain_sql = dialect.format_explain(sql)
    assert explain_sql == "EXPLAIN SELECT u.*, o.total FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE o.total > 100"
    assert "LEFT JOIN" in explain_sql

    # Test with subquery
    sql = "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders WHERE total > 100)"
    options = ExplainOptions(type=ExplainType.QUERYPLAN)
    explain_sql = dialect.format_explain(sql, options)
    assert explain_sql.startswith("EXPLAIN QUERY PLAN SELECT")
    assert "IN (SELECT" in explain_sql


def test_format_explain_with_options():
    """Test EXPLAIN formatting with different options"""
    dialect = SQLiteDialect(ConnectionConfig())
    sql = "SELECT * FROM users"

    # Test different formats
    # Note: SQLite ignores format option but we still test the interface
    for format_type in ['text', 'json']:
        options = ExplainOptions(format=format_type)
        explain_sql = dialect.format_explain(sql, options)
        assert explain_sql.startswith("EXPLAIN")

    # Test with costs option
    # Note: SQLite ignores costs option but we still test the interface
    options = ExplainOptions(costs=False)
    explain_sql = dialect.format_explain(sql, options)
    assert explain_sql.startswith("EXPLAIN")


def test_format_explain_integration():
    """Test EXPLAIN formatting integration with execute"""
    backend = SQLiteBackend(database=":memory:")

    # Create test table
    backend.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)
    backend.execute(
        "INSERT INTO users (name) VALUES (?), (?)",
        params=("test1", "test2")
    )

    # Test basic SELECT explain
    sql = "SELECT * FROM users WHERE name = ?"
    explain_sql = backend.dialect.format_explain(sql)
    result = backend.execute(explain_sql, params=("test1",), returning=True)
    assert result.data is not None
    assert len(result.data) > 0

    # Test SELECT with JOIN explain
    sql = """
        SELECT u1.name, u2.name 
        FROM users u1 
        JOIN users u2 ON u1.id = u2.id 
        WHERE u1.name = ?
    """
    explain_sql = backend.dialect.format_explain(
        sql,
        ExplainOptions(type=ExplainType.QUERYPLAN)
    )
    result = backend.execute(explain_sql, params=("test1",), returning=True)
    assert result.data is not None
    assert len(result.data) > 0
    # Assert the output which contains the key info.
    assert any("SCAN" in str(row) or "SEARCH" in str(row) for row in result.data)


def test_format_explain_with_transactions():
    """Test EXPLAIN formatting within transactions"""
    backend = SQLiteBackend(database=":memory:")

    with backend.transaction():
        # Create table and insert data
        backend.execute("""
            CREATE TABLE test (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """)
        backend.execute(
            "INSERT INTO test (value) VALUES (?), (?)",
            params=("test1", "test2")
        )

        # Test simple query
        sql = "SELECT * FROM test WHERE value LIKE ?"
        explain_sql = backend.dialect.format_explain(
            sql,
            ExplainOptions(type=ExplainType.QUERYPLAN)
        )
        result = backend.execute(explain_sql, params=("test%",), returning=True)
        assert result.data is not None
        assert len(result.data) > 0

        # Test aggregate query
        sql = "SELECT COUNT(*) as cnt FROM test GROUP BY value"
        explain_sql = backend.dialect.format_explain(sql)
        result = backend.execute(explain_sql, returning=True)
        assert result.data is not None
        assert len(result.data) > 0

    # The record has already existed when the transaction exited.
    result = backend.execute("SELECT COUNT(*) as cnt FROM test", returning=True)
    assert result.data[0]["cnt"] == 2
