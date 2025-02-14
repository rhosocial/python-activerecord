import pytest
from unittest.mock import patch, MagicMock

from src.rhosocial.activerecord.backend.errors import ReturningNotSupportedError, QueryError, OperationalError
from src.rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteReturningHandler
from src.rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend


def test_returning_not_supported():
    """Test RETURNING clause not supported in older SQLite versions"""
    # Mock SQLite version 3.34.0 (Before RETURNING support)
    handler = SQLiteReturningHandler((3, 34, 0))

    # Test is_supported property
    assert not handler.is_supported

    # Test format_clause raises ReturningNotSupportedError
    with pytest.raises(ReturningNotSupportedError) as exc_info:
        handler.format_clause()
    assert "SQLite version does not support RETURNING" in str(exc_info.value)

    # Test with specific columns
    with pytest.raises(ReturningNotSupportedError) as exc_info:
        handler.format_clause(columns=["id", "name"])
    assert "SQLite version does not support RETURNING" in str(exc_info.value)


def test_returning_with_columns():
    """Test RETURNING clause with specified columns"""
    # Mock SQLite version 3.35.0 (RETURNING supported)
    handler = SQLiteReturningHandler((3, 35, 0))

    # Test is_supported property
    assert handler.is_supported

    # Test single column
    result = handler.format_clause(columns=["id"])
    assert result == "RETURNING id"

    # Test multiple columns
    result = handler.format_clause(columns=["id", "name", "created_at"])
    assert result == "RETURNING id, name, created_at"

    # Test without columns (should return all columns)
    result = handler.format_clause()
    assert result == "RETURNING *"

    # Test empty columns list
    result = handler.format_clause(columns=[])
    assert result == "RETURNING *"


@patch('sqlite3.sqlite_version', '3.34.0')
def test_backend_returning_not_supported():
    """Test SQLite backend RETURNING functionality when not supported"""
    backend = SQLiteBackend(database=":memory:")

    # Test supports_returning property
    assert not backend.supports_returning

    # Test execute with RETURNING
    with pytest.raises(ReturningNotSupportedError) as exc_info:
        backend.execute(
            "INSERT INTO users (name) VALUES (?)",
            params=("test",),
            returning=True
        )
    assert "RETURNING clause not supported" in str(exc_info.value)

    # Test insert with RETURNING
    with pytest.raises(ReturningNotSupportedError) as exc_info:
        backend.insert(
            "users",
            {"name": "test"},
            returning=True
        )
    assert "RETURNING clause not supported" in str(exc_info.value)

    # Test update with RETURNING
    with pytest.raises(ReturningNotSupportedError) as exc_info:
        backend.update(
            "users",
            {"name": "updated"},
            "id = ?",
            (1,),
            returning=True
        )
    assert "RETURNING clause not supported" in str(exc_info.value)

    # Test delete with RETURNING
    with pytest.raises(ReturningNotSupportedError) as exc_info:
        backend.delete(
            "users",
            "id = ?",
            (1,),
            returning=True
        )
    assert "RETURNING clause not supported" in str(exc_info.value)


@patch('sqlite3.sqlite_version', '3.35.0')
def test_backend_returning_with_columns():
    """Test SQLite backend RETURNING functionality with specified columns"""
    backend = SQLiteBackend(database=":memory:")

    # Test supports_returning property
    assert backend.supports_returning

    # Create a test table
    backend.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            created_at TIMESTAMP
        )
    """)

    # Test insert with specific RETURNING columns
    result = backend.insert(
        "users",
        {
            "name": "test",
            "email": "test@example.com",
            "created_at": "2024-02-11 10:00:00"
        },
        returning=True,
        returning_columns=["id", "name"],
        force_returning=True,
    )
    assert result.data
    assert len(result.data) == 1
    assert "id" in result.data[0]
    assert "name" in result.data[0]
    assert "email" not in result.data[0]
    assert "created_at" not in result.data[0]

    # Test update with specific RETURNING columns
    result = backend.update(
        "users",
        {"name": "updated", "email": "updated@example.com"},
        "id = ?",
        (1,),
        returning=True,
        returning_columns=["name", "email"],
        force_returning=True,
    )
    assert result.data
    assert len(result.data) == 1
    assert "id" not in result.data[0]
    assert "name" in result.data[0]
    assert "email" in result.data[0]
    assert result.data[0]["name"] == "updated"
    assert result.data[0]["email"] == "updated@example.com"

    # Test delete with specific RETURNING columns
    result = backend.delete(
        "users",
        "id = ?",
        (1,),
        returning=True,
        returning_columns=["id"],
        force_returning=True,
    )
    assert result.data
    assert len(result.data) == 1
    assert "id" in result.data[0]
    assert "name" not in result.data[0]
    assert "email" not in result.data[0]
    assert result.data[0]["id"] == 1


@patch('sqlite3.sqlite_version', '3.35.0')
def test_returning_invalid_columns():
    """Test RETURNING clause with invalid column names"""
    backend = SQLiteBackend(database=":memory:")

    # Create test table
    backend.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT
        )
    """)

    # Test with single invalid column
    with pytest.raises(OperationalError) as exc_info:
        backend.insert(
            "users",
            {"name": "test", "email": "test@example.com"},
            returning=True,
            returning_columns=["nonexistent_column"],
            force_returning=True,
        )
    assert "no such column: nonexistent_column" in str(exc_info.value).lower()

    # Test with multiple invalid columns
    with pytest.raises(OperationalError) as exc_info:
        backend.insert(
            "users",
            {"name": "test", "email": "test@example.com"},
            returning=True,
            returning_columns=["invalid1", "invalid2"],
            force_returning=True,
        )
    assert "no such column: invalid1" in str(exc_info.value).lower()

    # Test with mix of valid and invalid columns
    with pytest.raises(OperationalError) as exc_info:
        backend.insert(
            "users",
            {"name": "test", "email": "test@example.com"},
            returning=True,
            returning_columns=["id", "nonexistent", "name"],
            force_returning=True,
        )
    assert "no such column: nonexistent" in str(exc_info.value).lower()

    # Test update with invalid columns
    with pytest.raises(OperationalError) as exc_info:
        backend.update(
            "users",
            {"name": "updated"},
            "id = ?",
            (1,),
            returning=True,
            returning_columns=["id", "fake_column"],
            force_returning=True,
        )
    assert "no such column: fake_column" in str(exc_info.value).lower()

    # Test delete with invalid columns
    with pytest.raises(OperationalError) as exc_info:
        backend.delete(
            "users",
            "id = ?",
            (1,),
            returning=True,
            returning_columns=["id", "ghost_column"],
            force_returning=True,
        )
    assert "no such column: ghost_column" in str(exc_info.value).lower()


def test_column_name_validation():
    """Test handling of column names with special characters"""
    backend = SQLiteBackend(database=":memory:")

    # Create test table with quoted column names
    backend.execute('''
        CREATE TABLE items (
            id INTEGER PRIMARY KEY,
            "special name" TEXT,
            "with.dot" TEXT,
            "with space" TEXT
        )
    ''')

    # Verify table creation
    result = backend.execute(
        "SELECT count(*) as cnt FROM sqlite_master WHERE type='table' AND name='items'",
        returning=True
    )
    assert result.data[0]['cnt'] == 1

    # Insert test data with quoted column names
    result = backend.insert(
        "items",
        {
            '"special name"': "test1",
            '"with.dot"': "test2",
            '"with space"': "test3"
        },
        returning=True,
        returning_columns=['"special name"', '"with.dot"', '"with space"'],
        force_returning=True,
    )

    assert result.data
    assert len(result.data) == 1
    # SQLite returns unquoted column names in result
    assert 'special name' in result.data[0]
    assert 'with.dot' in result.data[0]
    assert 'with space' in result.data[0]
    assert result.data[0]['special name'] == 'test1'
    assert result.data[0]['with.dot'] == 'test2'
    assert result.data[0]['with space'] == 'test3'

    # Test with SQL injection patterns in column names
    dangerous_patterns = [
        "column;",  # Semicolon
        "column--",  # Comment
        "columnUNIONx",  # UNION keyword
        "xSELECTcolumn",  # SELECT keyword
        "columnDROPx"  # DROP keyword
    ]

    for pattern in dangerous_patterns:
        with pytest.raises(ValueError) as exc_info:
            backend.insert(
                "items",
                {'"special name"': "test"},
                returning=True,
                returning_columns=[pattern],
                force_returning=True,
            )
        assert "Invalid column name" in str(exc_info.value)


def test_column_name_safety():
    """Test column name safety checks"""
    backend = SQLiteBackend(database=":memory:")

    # Create test table
    backend.execute("""
        CREATE TABLE data (
            id INTEGER PRIMARY KEY,
            name TEXT
        )
    """)

    # Verify table creation
    table_check = backend.execute(
        "SELECT count(*) as cnt FROM sqlite_master WHERE type='table' AND name='data'", returning=True
    )
    assert table_check.data[0]['cnt'] == 1

    # Test with potentially dangerous column names
    dangerous_columns = [
        'id;drop table data;',
        'id);drop table data;',
        'id union select id from data',
        'id",name);--',
        'id from data;--'
    ]

    for col in dangerous_columns:
        # All dangerous column names should be caught by validation
        with pytest.raises(ValueError) as exc_info:
            backend.insert(
                "data",
                {"name": "test"},
                returning=True,
                returning_columns=[col],
                force_returning=True,
            )
        assert "Invalid column name" in str(exc_info.value)

        # Verify table still exists after each attempt
        result = backend.execute(
            "SELECT count(*) as cnt FROM sqlite_master WHERE type='table' AND name='data'",
            returning=True
        )
        assert result.data[0]['cnt'] == 1

import sys
is_py38_39 = sys.version_info >= (3, 8) and sys.version_info < (3, 10)

py38_39_only = pytest.mark.skipif(
    not is_py38_39,
    reason="This test is specific to Python 3.8 and 3.9"
)
@py38_39_only
def test_python38_returning_with_quoted_columns():
    """Test RETURNING clause handling in Python 3.8/3.9 with quoted column names"""
    backend = SQLiteBackend(database=":memory:")

    # Create test table
    backend.execute('''
        CREATE TABLE special_items (
            id INTEGER PRIMARY KEY,
            "special name" TEXT,
            "with.dot" TEXT,
            "with space" TEXT
        )
    ''')

    # Single insert with returning
    result = backend.insert(
        "special_items",
        {
            '"special name"': "test1",
            '"with.dot"': "test2",
            '"with space"': "test3"
        },
        returning=True,
        returning_columns=['"special name"', '"with.dot"', '"with space"'],
        force_returning=True,
    )

    # Verify result structure
    assert result.affected_rows == 0  # For known reasons, the return value here is always zero.
    assert len(result.data) == 1
    row = result.data[0]
    assert 'special name' in row
    assert 'with.dot' in row
    assert 'with space' in row
    assert row['special name'] == 'test1'
    assert row['with.dot'] == 'test2'
    assert row['with space'] == 'test3'

    # Multiple sequential inserts
    for i in range(3):
        result = backend.insert(
            "special_items",
            {
                '"special name"': f"batch{i}",
                '"with.dot"': f"dot{i}",
                '"with space"': f"space{i}"
            },
            returning=True,
            returning_columns=['"special name"', '"with.dot"', '"with space"'],
            force_returning=True,
        )
        assert result.affected_rows == 1
        assert len(result.data) == 1
        row = result.data[0]
        assert row['special name'] == f"batch{i}"
        assert row['with.dot'] == f"dot{i}"
        assert row['with space'] == f"space{i}"

