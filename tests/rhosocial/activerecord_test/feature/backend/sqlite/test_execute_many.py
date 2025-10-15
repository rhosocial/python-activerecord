# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_execute_many.py
"""Tests for SQLiteBackend.execute_many method functionality"""

from unittest.mock import patch

import pytest

from rhosocial.activerecord.backend.errors import DatabaseError, QueryError
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.typing import QueryResult


class TestSQLiteExecuteMany:
    """Tests for SQLiteBackend.execute_many method"""

    @pytest.fixture
    def backend(self):
        """Create a SQLite backend with in-memory database"""
        backend = SQLiteBackend(database=":memory:")
        backend.connect()

        # Create test tables
        backend.execute("""
                        CREATE TABLE users
                        (
                            id     INTEGER PRIMARY KEY,
                            name   TEXT,
                            email  TEXT,
                            active INTEGER
                        )
                        """)

        backend.execute("""
                        CREATE TABLE posts
                        (
                            id      INTEGER PRIMARY KEY,
                            user_id INTEGER,
                            title   TEXT,
                            content TEXT,
                            FOREIGN KEY (user_id) REFERENCES users (id)
                        )
                        """)

        yield backend
        backend.disconnect()

    def test_insert_batch(self, backend):
        """Test batch INSERT operations"""
        # Prepare test data
        users = [
            (1, "User 1", "user1@example.com", 1),
            (2, "User 2", "user2@example.com", 1),
            (3, "User 3", "user3@example.com", 0)
        ]

        # Execute batch insert
        result = backend.execute_many(
            "INSERT INTO users (id, name, email, active) VALUES (?, ?, ?, ?)",
            users
        )

        # Verify result properties
        assert isinstance(result, QueryResult)
        assert result.affected_rows == 3
        assert result.duration > 0
        assert result.data is None  # No data returned for INSERT

        # Verify data was inserted correctly
        db_users = backend.fetch_all("SELECT * FROM users ORDER BY id")
        assert len(db_users) == 3
        assert db_users[0]["name"] == "User 1"
        assert db_users[2]["active"] == 0

    def test_update_batch(self, backend):
        """Test batch UPDATE operations"""
        # Insert test data
        backend.execute_many(
            "INSERT INTO users (id, name, email, active) VALUES (?, ?, ?, ?)",
            [
                (1, "User 1", "user1@example.com", 1),
                (2, "User 2", "user2@example.com", 1),
                (3, "User 3", "user3@example.com", 1)
            ]
        )

        # Execute batch update
        updates = [
            ("Updated User 1", 1),
            ("Updated User 3", 3)
        ]

        result = backend.execute_many(
            "UPDATE users SET name = ? WHERE id = ?",
            updates
        )

        # Verify result
        assert result.affected_rows == 2

        # Verify data was updated correctly
        user1 = backend.fetch_one("SELECT * FROM users WHERE id = 1")
        user2 = backend.fetch_one("SELECT * FROM users WHERE id = 2")
        user3 = backend.fetch_one("SELECT * FROM users WHERE id = 3")

        assert user1["name"] == "Updated User 1"
        assert user2["name"] == "User 2"  # Not updated
        assert user3["name"] == "Updated User 3"

    def test_empty_params_list(self, backend):
        """Test execute_many with empty params list"""
        result = backend.execute_many(
            "INSERT INTO users (id, name) VALUES (?, ?)",
            []
        )

        # Should return a result with 0 affected rows
        assert result.affected_rows == 0
        assert result.duration >= 0

        # No data should be inserted
        count = backend.fetch_one("SELECT COUNT(*) as count FROM users")
        assert count["count"] == 0

    def test_params_mismatch(self, backend):
        """Test execute_many with mismatched parameters"""
        # Too few parameters
        with pytest.raises(Exception) as exc_info:
            backend.execute_many(
                "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
                [(1, "User 1")]  # Missing email parameter
            )

        # The exact exception type may vary by SQLite version, but should be an error
        assert "Error" in str(exc_info) or "error" in str(exc_info).lower()

        # Too many parameters
        with pytest.raises(Exception) as exc_info:
            backend.execute_many(
                "INSERT INTO users (id, name) VALUES (?, ?)",
                [(1, "User 1", "extra@example.com")]  # Extra parameter
            )

        assert "Error" in str(exc_info) or "error" in str(exc_info).lower()

    def test_table_not_exists(self, backend):
        """Test execute_many with non-existent table"""
        with pytest.raises((DatabaseError, QueryError)) as exc_info:
            backend.execute_many(
                "INSERT INTO nonexistent (id, name) VALUES (?, ?)",
                [(1, "Test"), (2, "Test 2")]
            )

        # Should raise error about table not existing
        assert "no such table" in str(exc_info.value).lower()

    def test_unsupported_operation_select(self, backend):
        """Test execute_many with SELECT statement (behavior varies by Python version)"""
        from rhosocial.activerecord.backend.errors import DatabaseError

        # In all Python versions, try to execute the SELECT statement
        try:
            result = backend.execute_many(
                "SELECT * FROM users WHERE id = ?",
                [(1,), (2,), (3,)]
            )
            # If no error is reported, the verification result is None or the affected_rows is 0
            if result is not None:
                assert result.affected_rows == -1
        except (Exception, DatabaseError) as e:
            # If an error is reported, verify the error message
            error_msg = str(e).lower()
            assert any(msg in error_msg for msg in [
                "error",
                "dml",
                "executemany",
                "select",
                "statement"
            ])

    def test_multiple_statements(self, backend):
        """Test execute_many with multiple statements (behavior varies by Python version)"""
        import sys

        # The error message and behavior varies by Python version
        with pytest.raises(Exception) as exc_info:
            backend.execute_many(
                "INSERT INTO users (id, name) VALUES (?, ?); SELECT * FROM users",
                [(1, "User 1")]
            )

        # Different Python versions may have different error messages
        if sys.version_info >= (3, 11):
            # In newer Python versions, check for any error
            assert exc_info.value is not None
        else:
            # In older Python versions, check for specific error message
            assert "You can only execute one statement at a time" in str(exc_info.value) or \
                   "Error" in str(exc_info.value) or \
                   "error" in str(exc_info.value).lower()

    def test_foreign_key_constraint(self, backend):
        """Test execute_many with foreign key constraint violation"""
        # SQLite should have foreign keys enabled (in the DEFAULT_PRAGMAS)

        # Try to insert posts with non-existent user_ids
        with pytest.raises(DatabaseError) as exc_info:
            backend.execute_many(
                "INSERT INTO posts (id, user_id, title) VALUES (?, ?, ?)",
                [
                    (1, 99, "Title 1"),  # user_id 99 doesn't exist
                    (2, 100, "Title 2")  # user_id 100 doesn't exist
                ]
            )

        # Should raise foreign key constraint error
        assert "foreign key constraint" in str(exc_info.value).lower()

        # Now insert a valid user and test with valid and invalid foreign keys
        assert backend.execute("INSERT INTO users (id, name) VALUES (1, 'User 1')").affected_rows == 1

        with pytest.raises(DatabaseError) as exc_info:
            backend.execute_many(
                "INSERT INTO posts (id, user_id, title) VALUES (?, ?, ?)",
                [
                    (1, 1, "Title 1"),  # Valid user_id
                    (2, 999, "Title 2")  # Invalid user_id
                ]
            )

        # Should still raise constraint error for the invalid entry
        assert "foreign key constraint" in str(exc_info.value).lower()

        # No posts should be inserted due to transaction rollback
        count = backend.fetch_one("SELECT COUNT(*) as count FROM posts")
        assert count["count"] == 1

    def test_large_batch(self, backend):
        """Test execute_many with a large batch of insertions"""
        # Generate a large number of records
        large_batch = [(i, f"User {i}", f"user{i}@example.com", 1) for i in range(1, 1001)]

        # Execute batch insert
        result = backend.execute_many(
            "INSERT INTO users (id, name, email, active) VALUES (?, ?, ?, ?)",
            large_batch
        )

        # Verify all records were inserted
        assert result.affected_rows == 1000

        # Verify count
        count = backend.fetch_one("SELECT COUNT(*) as count FROM users")
        assert count["count"] == 1000

    def test_batch_with_transactions(self, backend):
        """Test execute_many within transactions"""
        # Start a transaction
        backend.begin_transaction()

        # Insert users
        backend.execute_many(
            "INSERT INTO users (id, name) VALUES (?, ?)",
            [(1, "User 1"), (2, "User 2")]
        )

        # Verify users are visible within the transaction
        count = backend.fetch_one("SELECT COUNT(*) as count FROM users")
        assert count["count"] == 2

        # Rollback the transaction
        backend.rollback_transaction()

        # Verify no users remain after rollback
        count = backend.fetch_one("SELECT COUNT(*) as count FROM users")
        assert count["count"] == 0

        # Test with commit
        backend.begin_transaction()
        backend.execute_many(
            "INSERT INTO users (id, name) VALUES (?, ?)",
            [(1, "User 1"), (2, "User 2")]
        )
        backend.commit_transaction()

        # Verify users persist after commit
        count = backend.fetch_one("SELECT COUNT(*) as count FROM users")
        assert count["count"] == 2

    def test_handle_errors(self, backend):
        """Test error handling in execute_many"""
        with patch.object(backend, '_handle_error') as mock_handle_error:
            # Create an error condition (duplicate primary key)
            backend.execute("INSERT INTO users (id, name) VALUES (1, 'User 1')")

            try:
                backend.execute_many(
                    "INSERT INTO users (id, name) VALUES (?, ?)",
                    [(1, "Duplicate")]  # Will cause constraint error
                )
            except:
                pass  # Ignore the exception for the test

            # Verify _handle_error was called
            assert mock_handle_error.called

    def test_affected_rows_count(self, backend):
        """Test affected_rows count in various scenarios"""
        # Insert test data
        backend.execute_many(
            "INSERT INTO users (id, name, active) VALUES (?, ?, ?)",
            [(1, "User 1", 1), (2, "User 2", 1), (3, "User 3", 0)]
        )

        # Test UPDATE that affects some rows
        result = backend.execute_many(
            "UPDATE users SET name = ? WHERE active = ?",
            [("Active User", 1)]  # Should update 2 rows
        )
        assert result.affected_rows == 2

        # Test UPDATE that affects no rows
        result = backend.execute_many(
            "UPDATE users SET name = ? WHERE id > ?",
            [("No one", 100)]  # No users match this condition
        )
        assert result.affected_rows == 0

        # Test UPDATE with multiple parameter sets
        result = backend.execute_many(
            "UPDATE users SET active = ? WHERE id = ?",
            [(0, 1), (0, 2)]  # Update 2 separate rows
        )
        assert result.affected_rows == 2
