# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_cte.py
from unittest.mock import patch

import pytest

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteCTEHandler


def test_cte_support_detection():
    """Test detection of CTE support in different SQLite versions"""
    # Test with version before CTE support (3.8.2)
    older_handler = SQLiteCTEHandler((3, 8, 2))
    assert not older_handler.is_supported
    assert not older_handler.supports_recursive
    assert not older_handler.supports_compound_recursive
    assert not older_handler.supports_multiple_ctes
    assert not older_handler.supports_cte_in_dml
    assert not older_handler.supports_materialized_hint

    # Test with version that supports basic CTE and recursive CTE (3.8.3)
    basic_handler = SQLiteCTEHandler((3, 8, 3))
    assert basic_handler.is_supported
    assert basic_handler.supports_recursive
    assert not basic_handler.supports_compound_recursive
    assert basic_handler.supports_multiple_ctes
    assert basic_handler.supports_cte_in_dml
    assert not basic_handler.supports_materialized_hint

    # Test with version that supports compound recursive CTE (3.34.0)
    compound_handler = SQLiteCTEHandler((3, 34, 0))
    assert compound_handler.is_supported
    assert compound_handler.supports_recursive
    assert compound_handler.supports_compound_recursive
    assert compound_handler.supports_multiple_ctes
    assert compound_handler.supports_cte_in_dml
    assert not compound_handler.supports_materialized_hint

    # Test with version that supports materialization hints (3.35.0)
    newer_handler = SQLiteCTEHandler((3, 35, 0))
    assert newer_handler.is_supported
    assert newer_handler.supports_recursive
    assert newer_handler.supports_compound_recursive
    assert newer_handler.supports_multiple_ctes
    assert newer_handler.supports_cte_in_dml
    assert newer_handler.supports_materialized_hint


def test_cte_formatting_basic():
    """Test basic CTE formatting works regardless of feature support"""
    # Even with older versions, formatting should still work
    older_handler = SQLiteCTEHandler((3, 8, 2))

    # Basic CTE format
    result = older_handler.format_cte("temp_cte", "SELECT * FROM users")
    assert result == "temp_cte AS (SELECT * FROM users)"

    # CTE with column definitions
    result = older_handler.format_cte(
        "temp_cte",
        "SELECT id, name FROM users",
        columns=["user_id", "user_name"]
    )
    assert result == "temp_cte(user_id, user_name) AS (SELECT id, name FROM users)"

    # WITH clause formatting
    result = older_handler.format_with_clause([
        {"name": "cte1", "query": "SELECT 1 AS val"}
    ])
    assert result == "WITH cte1 AS (SELECT 1 AS val)"

    # Multiple CTEs
    result = older_handler.format_with_clause([
        {"name": "cte1", "query": "SELECT 1 AS val"},
        {"name": "cte2", "query": "SELECT 2 AS val"}
    ])
    assert "WITH cte1 AS (SELECT 1 AS val), cte2 AS (SELECT 2 AS val)" == result


def test_recursive_cte_formatting():
    """Test simple recursive CTE formatting works regardless of feature support"""
    # Using handler for version before CTE support
    older_handler = SQLiteCTEHandler((3, 8, 2))

    # Simple recursive CTE should still format correctly even when not supported
    result = older_handler.format_with_clause(
        [{
            "name": "numbers",
            "query": "SELECT 1 as n UNION ALL SELECT n+1 FROM numbers WHERE n < 10",
            "recursive": True
        }]
    )
    assert result == "WITH RECURSIVE numbers AS (SELECT 1 as n UNION ALL SELECT n+1 FROM numbers WHERE n < 10)"


def test_compound_recursive_cte_formatting():
    """Test compound recursive CTE formatting works regardless of feature support"""
    # Using handler for version before compound recursive CTE support
    older_handler = SQLiteCTEHandler((3, 8, 3))
    assert not older_handler.supports_compound_recursive

    # Compound recursive CTE should still format correctly even if not supported in the version
    compound_query = """
                     SELECT id, name, 1 as level \
                     FROM categories \
                     WHERE parent_id IS NULL
                     UNION ALL
                     SELECT c.id, c.name, rc.level + 1 \
                     FROM categories c \
                              JOIN rec_categories rc ON c.parent_id = rc.id \
                     """

    result = older_handler.format_with_clause(
        [{
            "name": "rec_categories",
            "query": compound_query.strip(),
            "recursive": True
        }]
    )

    assert "WITH RECURSIVE rec_categories AS" in result

    # Test with version that supports compound recursive CTE
    newer_handler = SQLiteCTEHandler((3, 34, 0))
    assert newer_handler.supports_compound_recursive

    # The format result should be the same regardless of support
    newer_result = newer_handler.format_with_clause(
        [{
            "name": "rec_categories",
            "query": compound_query.strip(),
            "recursive": True
        }]
    )

    assert result == newer_result  # Format result should be identical


def test_materialization_hint_formatting():
    """Test materialization hint formatting depends on feature support"""
    # Test with older SQLite version (before 3.35.0) - hints should be ignored
    older_handler = SQLiteCTEHandler((3, 8, 3))

    # With materialized=True, but not supported
    result = older_handler.format_cte(
        "temp_cte",
        "SELECT * FROM users",
        materialized=True
    )
    # Hint should be ignored because version doesn't support it
    assert result == "temp_cte AS (SELECT * FROM users)"

    # Test with newer SQLite version (3.35.0+) - hints should be applied
    newer_handler = SQLiteCTEHandler((3, 35, 0))

    # With materialized=True
    result = newer_handler.format_cte(
        "temp_cte",
        "SELECT * FROM users",
        materialized=True
    )
    assert result == "temp_cte AS MATERIALIZED (SELECT * FROM users)"

    # With materialized=False
    result = newer_handler.format_cte(
        "temp_cte",
        "SELECT * FROM users",
        materialized=False
    )
    assert result == "temp_cte AS NOT MATERIALIZED (SELECT * FROM users)"

    # Test in format_with_clause
    result = newer_handler.format_with_clause([{
        "name": "temp_cte",
        "query": "SELECT * FROM users",
        "materialized": True
    }])
    assert result == "WITH temp_cte AS MATERIALIZED (SELECT * FROM users)"

    # Test with materialized=None (should not add hint)
    result = newer_handler.format_cte(
        "temp_cte",
        "SELECT * FROM users",
        materialized=None
    )
    assert result == "temp_cte AS (SELECT * FROM users)"


def test_cte_name_validation():
    """Test CTE name validation for security"""
    handler = SQLiteCTEHandler((3, 8, 3))

    # Test valid names
    assert handler.validate_cte_name("valid_name") == "valid_name"
    assert handler.validate_cte_name("ValidName123") == "ValidName123"
    assert handler.validate_cte_name("valid_name_with_underscore") == "valid_name_with_underscore"

    # Test invalid names
    with pytest.raises(ValueError) as exc_info:
        handler.validate_cte_name("name;")
    assert "Invalid CTE name" in str(exc_info.value)

    with pytest.raises(ValueError) as exc_info:
        handler.validate_cte_name("name--")
    assert "Invalid CTE name" in str(exc_info.value)

    with pytest.raises(ValueError) as exc_info:
        handler.validate_cte_name("name'")
    assert "Invalid CTE name" in str(exc_info.value)

    # Test empty name
    with pytest.raises(ValueError) as exc_info:
        handler.validate_cte_name("")
    assert "CTE name cannot be empty" in str(exc_info.value)

    with pytest.raises(ValueError) as exc_info:
        handler.validate_cte_name("   ")
    assert "CTE name cannot be empty" in str(exc_info.value)


def test_complex_cte_formatting():
    """Test more complex CTE scenarios formatting"""
    handler = SQLiteCTEHandler((3, 8, 3))

    # Test nested CTEs
    result = handler.format_with_clause([
        {
            "name": "level1",
            "query": "SELECT 1 as id, 'Level 1' as name"
        },
        {
            "name": "level2",
            "query": "SELECT id + 1 as id, name || ' > Level 2' as name FROM level1"
        },
        {
            "name": "level3",
            "query": "SELECT id + 1 as id, name || ' > Level 3' as name FROM level2"
        }
    ])

    assert "WITH level1 AS " in result
    assert "level2 AS (SELECT id + 1 as id, name || ' > Level 2' as name FROM level1)" in result
    assert "level3 AS (SELECT id + 1 as id, name || ' > Level 3' as name FROM level2)" in result

    # Test empty CTE list
    empty_result = handler.format_with_clause([])
    assert empty_result == ""


@patch('sqlite3.sqlite_version', '3.8.2')
def test_dialect_cte_support_detection():
    """Test CTE support detection through SQLite backend dialect"""
    backend = SQLiteBackend(database=":memory:")

    # Create a dialect to check CTE support
    dialect = backend.dialect
    assert not dialect.cte_handler.is_supported
    assert not dialect.cte_handler.supports_materialized_hint
    assert not dialect.cte_handler.supports_compound_recursive


@patch('sqlite3.sqlite_version', '3.8.3')
def test_execute_cte_query():
    """Test executing CTE queries (should check support before execution)"""
    backend = SQLiteBackend(database=":memory:")

    # Create test table
    backend.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")

    # Insert test data
    backend.execute("INSERT INTO users (name) VALUES ('User 1')")
    backend.execute("INSERT INTO users (name) VALUES ('User 2')")

    # Verify CTE support
    assert backend.dialect.cte_handler.is_supported
    assert backend.dialect.cte_handler.supports_recursive
    assert not backend.dialect.cte_handler.supports_compound_recursive

    # Test simple CTE
    result = backend.execute(
        "WITH user_cte AS (SELECT * FROM users) SELECT * FROM user_cte",
        returning=True
    )
    assert len(result.data) == 2

    # Test CTE with column definition
    result = backend.execute(
        "WITH user_cte(user_id, user_name) AS (SELECT id, name FROM users) SELECT * FROM user_cte",
        returning=True
    )
    assert len(result.data) == 2
    assert "user_id" in result.data[0]
    assert "user_name" in result.data[0]


@patch('sqlite3.sqlite_version', '3.34.0')
def test_execute_compound_recursive_cte():
    """Test executing compound recursive CTE queries"""
    backend = SQLiteBackend(database=":memory:")

    # Verify compound recursive CTE support
    assert backend.dialect.cte_handler.is_supported
    assert backend.dialect.cte_handler.supports_recursive
    assert backend.dialect.cte_handler.supports_compound_recursive
    assert not backend.dialect.cte_handler.supports_materialized_hint

    # Create test table
    backend.execute("""
                    CREATE TABLE categories
                    (
                        id        INTEGER PRIMARY KEY,
                        name      TEXT,
                        parent_id INTEGER NULL
                    )
                    """)

    # Insert test data
    backend.execute("INSERT INTO categories (id, name, parent_id) VALUES (1, 'Root', NULL)")
    backend.execute("INSERT INTO categories (id, name, parent_id) VALUES (2, 'Child', 1)")
    backend.execute("INSERT INTO categories (id, name, parent_id) VALUES (3, 'Grandchild', 2)")

    # Test compound recursive CTE
    result = backend.execute(
        """
        WITH RECURSIVE category_tree AS (SELECT id, name, parent_id, 1 as depth
                                         FROM categories
                                         WHERE parent_id IS NULL
                                         UNION ALL
                                         SELECT c.id, c.name, c.parent_id, ct.depth + 1
                                         FROM categories c
                                                  JOIN category_tree ct ON c.parent_id = ct.id)
        SELECT *
        FROM category_tree
        ORDER BY depth
        """,
        returning=True
    )

    assert len(result.data) == 3
    assert result.data[0]['depth'] == 1  # Root
    assert result.data[1]['depth'] == 2  # Child
    assert result.data[2]['depth'] == 3  # Grandchild


@patch('sqlite3.sqlite_version', '3.35.0')
def test_execute_materialized_cte_query():
    """Test executing CTE queries with materialization hints"""
    backend = SQLiteBackend(database=":memory:")

    # Create test table
    backend.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")

    # Insert test data
    backend.execute("INSERT INTO users (name) VALUES ('User 1')")
    backend.execute("INSERT INTO users (name) VALUES ('User 2')")

    # Verify CTE and materialization support
    assert backend.dialect.cte_handler.is_supported
    assert backend.dialect.cte_handler.supports_recursive
    assert backend.dialect.cte_handler.supports_compound_recursive
    assert backend.dialect.cte_handler.supports_materialized_hint

    # Test materialized CTE
    result = backend.execute(
        "WITH user_cte AS MATERIALIZED (SELECT * FROM users) SELECT * FROM user_cte",
        returning=True
    )
    assert len(result.data) == 2

    # Test not materialized CTE
    result = backend.execute(
        "WITH user_cte AS NOT MATERIALIZED (SELECT * FROM users) SELECT * FROM user_cte",
        returning=True
    )
    assert len(result.data) == 2

    # Test mixed materialization
    result = backend.execute(
        """WITH cte1 AS MATERIALIZED (SELECT * FROM users), cte2 AS NOT MATERIALIZED (SELECT * FROM users)
        SELECT *
        FROM cte1
                 JOIN cte2 ON cte1.id = cte2.id""",
        returning=True
    )
