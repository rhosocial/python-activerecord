# tests/rhosocial/activerecord_test/feature/backend/dml/test_execute_many_async.py
"""Async twin of test_execute_many.py using AsyncSQLiteBackend.execute_many."""
from unittest.mock import patch

import pytest
import pytest_asyncio

from rhosocial.activerecord.backend.errors import DatabaseError, QueryError
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.result import QueryResult


class TestAsyncSQLiteExecuteMany:
    """Tests for AsyncSQLiteBackend.execute_many method"""

    @pytest_asyncio.fixture
    async def backend(self):
        """Create an async SQLite backend with in-memory database"""
        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()

        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType

        await backend.execute(
            """
                        CREATE TABLE users
                        (
                            id     INTEGER PRIMARY KEY,
                            name   TEXT,
                            email  TEXT,
                            active INTEGER
                        )
                        """,
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )

        await backend.execute(
            """
                        CREATE TABLE posts
                        (
                            id      INTEGER PRIMARY KEY,
                            user_id INTEGER,
                            title   TEXT,
                            content TEXT,
                            FOREIGN KEY (user_id) REFERENCES users (id)
                        )
                        """,
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )

        yield backend
        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_insert_batch(self, backend):
        """Test batch INSERT operations"""
        users = [
            (1, "User 1", "user1@example.com", 1),
            (2, "User 2", "user2@example.com", 1),
            (3, "User 3", "user3@example.com", 0),
        ]

        result = await backend.execute_many("INSERT INTO users (id, name, email, active) VALUES (?, ?, ?, ?)", users)

        assert isinstance(result, QueryResult)
        assert result.affected_rows == 3
        assert result.duration > 0
        assert result.data is None

        db_users = await backend.fetch_all("SELECT * FROM users ORDER BY id")
        assert len(db_users) == 3
        assert db_users[0]["name"] == "User 1"
        assert db_users[2]["active"] == 0

    @pytest.mark.asyncio
    async def test_update_batch(self, backend):
        """Test batch UPDATE operations"""
        await backend.execute_many(
            "INSERT INTO users (id, name, email, active) VALUES (?, ?, ?, ?)",
            [
                (1, "User 1", "user1@example.com", 1),
                (2, "User 2", "user2@example.com", 1),
                (3, "User 3", "user3@example.com", 1),
            ],
        )

        updates = [("Updated User 1", 1), ("Updated User 3", 3)]

        result = await backend.execute_many("UPDATE users SET name = ? WHERE id = ?", updates)
        assert result.affected_rows == 2

        user1 = await backend.fetch_one("SELECT * FROM users WHERE id = 1")
        user2 = await backend.fetch_one("SELECT * FROM users WHERE id = 2")
        user3 = await backend.fetch_one("SELECT * FROM users WHERE id = 3")

        assert user1["name"] == "Updated User 1"
        assert user2["name"] == "User 2"
        assert user3["name"] == "Updated User 3"

    @pytest.mark.asyncio
    async def test_empty_params_list(self, backend):
        """Test execute_many with empty params list"""
        result = await backend.execute_many("INSERT INTO users (id, name) VALUES (?, ?)", [])

        assert result.affected_rows == 0
        assert result.duration >= 0

        count = await backend.fetch_one("SELECT COUNT(*) as count FROM users")
        assert count["count"] == 0

    @pytest.mark.asyncio
    async def test_params_mismatch(self, backend):
        """Test execute_many with mismatched parameters"""
        with pytest.raises(Exception) as exc_info:
            await backend.execute_many(
                "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
                [(1, "User 1")],  # Missing email parameter
            )
        assert "Error" in str(exc_info) or "error" in str(exc_info).lower()

        with pytest.raises(Exception) as exc_info:
            await backend.execute_many(
                "INSERT INTO users (id, name) VALUES (?, ?)",
                [(1, "User 1", "extra@example.com")],  # Extra parameter
            )
        assert "Error" in str(exc_info) or "error" in str(exc_info).lower()

    @pytest.mark.asyncio
    async def test_table_not_exists(self, backend):
        """Test execute_many with non-existent table"""
        with pytest.raises((DatabaseError, QueryError)) as exc_info:
            await backend.execute_many("INSERT INTO nonexistent (id, name) VALUES (?, ?)", [(1, "Test"), (2, "Test 2")])
        assert "no such table" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_unsupported_operation_select(self, backend):
        """Test execute_many with SELECT statement (behavior varies by Python version)"""
        from rhosocial.activerecord.backend.errors import DatabaseError

        try:
            result = await backend.execute_many("SELECT * FROM users WHERE id = ?", [(1,), (2,), (3,)])
            if result is not None:
                assert result.affected_rows == -1
        except (Exception, DatabaseError) as e:
            error_msg = str(e).lower()
            assert any(msg in error_msg for msg in ["error", "dml", "executemany", "select", "statement"])

    @pytest.mark.asyncio
    async def test_multiple_statements(self, backend):
        """Test execute_many with multiple statements (behavior varies by Python version)"""
        import sys

        with pytest.raises(Exception) as exc_info:
            await backend.execute_many("INSERT INTO users (id, name) VALUES (?, ?); SELECT * FROM users", [(1, "User 1")])

        if sys.version_info >= (3, 11):
            assert exc_info.value is not None
        else:
            assert (
                "You can only execute one statement at a time" in str(exc_info.value)
                or "Error" in str(exc_info.value)
                or "error" in str(exc_info.value).lower()
            )

    @pytest.mark.asyncio
    async def test_foreign_key_constraint(self, backend):
        """Test execute_many with foreign key constraint violation"""
        with pytest.raises(DatabaseError) as exc_info:
            await backend.execute_many(
                "INSERT INTO posts (id, user_id, title) VALUES (?, ?, ?)",
                [
                    (1, 99, "Title 1"),  # user_id 99 doesn't exist
                    (2, 100, "Title 2"),  # user_id 100 doesn't exist
                ],
            )
        assert "foreign key constraint" in str(exc_info.value).lower()

        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType

        result = await backend.execute(
            "INSERT INTO users (id, name) VALUES (1, 'User 1')",
            (),
            options=ExecutionOptions(stmt_type=StatementType.INSERT),
        )
        assert result is not None

        with pytest.raises(DatabaseError) as exc_info:
            await backend.execute_many(
                "INSERT INTO posts (id, user_id, title) VALUES (?, ?, ?)",
                [
                    (1, 1, "Title 1"),  # Valid user_id
                    (2, 999, "Title 2"),  # Invalid user_id
                ],
            )
        assert "foreign key constraint" in str(exc_info.value).lower()

        count = await backend.fetch_one("SELECT COUNT(*) as count FROM posts")
        assert count["count"] == 1

    @pytest.mark.asyncio
    async def test_large_batch(self, backend):
        """Test execute_many with a large batch of insertions"""
        large_batch = [(i, f"User {i}", f"user{i}@example.com", 1) for i in range(1, 1001)]

        result = await backend.execute_many("INSERT INTO users (id, name, email, active) VALUES (?, ?, ?, ?)", large_batch)
        assert result.affected_rows == 1000

        count = await backend.fetch_one("SELECT COUNT(*) as count FROM users")
        assert count["count"] == 1000

    @pytest.mark.asyncio
    async def test_batch_with_transactions(self, backend):
        """Test execute_many within transactions"""
        await backend.begin_transaction()

        await backend.execute_many("INSERT INTO users (id, name) VALUES (?, ?)", [(1, "User 1"), (2, "User 2")])

        count = await backend.fetch_one("SELECT COUNT(*) as count FROM users")
        assert count["count"] == 2

        await backend.rollback_transaction()

        count = await backend.fetch_one("SELECT COUNT(*) as count FROM users")
        assert count["count"] == 0

        await backend.begin_transaction()
        await backend.execute_many("INSERT INTO users (id, name) VALUES (?, ?)", [(1, "User 1"), (2, "User 2")])
        await backend.commit_transaction()

        count = await backend.fetch_one("SELECT COUNT(*) as count FROM users")
        assert count["count"] == 2

    @pytest.mark.asyncio
    async def test_handle_errors(self, backend):
        """Test error handling in execute_many"""
        with patch.object(backend, "_handle_error") as mock_handle_error:
            from rhosocial.activerecord.backend.options import ExecutionOptions
            from rhosocial.activerecord.backend.schema import StatementType

            await backend.execute(
                "INSERT INTO users (id, name) VALUES (1, 'User 1')",
                (),
                options=ExecutionOptions(stmt_type=StatementType.INSERT),
            )

            try:
                await backend.execute_many(
                    "INSERT INTO users (id, name) VALUES (?, ?)",
                    [(1, "Duplicate")],  # Will cause constraint error
                )
            except:  # noqa: E722
                pass

            assert mock_handle_error.called

    @pytest.mark.asyncio
    async def test_affected_rows_count(self, backend):
        """Test affected_rows count in various scenarios"""
        await backend.execute_many(
            "INSERT INTO users (id, name, active) VALUES (?, ?, ?)",
            [(1, "User 1", 1), (2, "User 2", 1), (3, "User 3", 0)],
        )

        result = await backend.execute_many(
            "UPDATE users SET name = ? WHERE active = ?",
            [("Active User", 1)],  # Should update 2 rows
        )
        assert result.affected_rows == 2

        result = await backend.execute_many(
            "UPDATE users SET name = ? WHERE id > ?",
            [("No one", 100)],  # No users match this condition
        )
        assert result.affected_rows == 0

        result = await backend.execute_many(
            "UPDATE users SET active = ? WHERE id = ?",
            [(0, 1), (0, 2)],  # Update 2 separate rows
        )
        assert result.affected_rows == 2
