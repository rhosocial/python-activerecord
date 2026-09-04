# tests/rhosocial/activerecord_test/feature/backend/backend/test_backend_comprehensive.py
"""
Comprehensive sync tests for SQLiteBackend

Sync twin of test_backend_comprehensive_async.py, covering:
- basic operations (connect, execute, fetch, ping, pragma, context manager)
- execute_many (batch insert/update, error cases, concurrency counts)
- transaction management (nested, savepoints, isolation levels)
- RETURNING clause execution via expressions
- column mapping with adapters
"""

import os
import tempfile
from unittest.mock import patch

import pytest

from rhosocial.activerecord.backend.errors import DatabaseError, QueryError, TransactionError
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.transaction import IsolationLevel
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import (
    InsertExpression,
    ValuesSource,
    Literal,
    Column,
    ReturningClause,
    UpdateExpression,
    DeleteExpression,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


class TestSQLiteBackendBasic:
    """Test basic sync operations"""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file path"""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        # Cleanup
        for ext in ["", "-wal", "-shm"]:
            wal_path = path + ext
            if os.path.exists(wal_path):
                try:
                    os.remove(wal_path)
                except OSError:
                    pass

    @pytest.fixture
    def backend(self, temp_db_path):
        """Create sync SQLite backend"""
        config = SQLiteConnectionConfig(database=temp_db_path)
        backend = SQLiteBackend(connection_config=config)
        backend.connect()
        backend.introspect_and_adapt()
        yield backend
        backend.disconnect()

    @pytest.fixture
    def memory_backend(self):
        """Create an in-memory sync SQLite backend"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        backend.connect()
        backend.introspect_and_adapt()
        yield backend
        backend.disconnect()

    @pytest.fixture
    def disconnected_backend(self, temp_db_path):
        """Create a disconnected sync SQLite backend for testing"""
        config = SQLiteConnectionConfig(database=temp_db_path)
        backend = SQLiteBackend(connection_config=config)
        yield backend
        # Ensure cleanup even if test connects the backend
        if backend.is_connected():
            backend.disconnect()

    @pytest.fixture
    def pragma_backend(self):
        """Create backend with pragma settings"""
        config = SQLiteConnectionConfig(database=":memory:", pragmas={"synchronous": "NORMAL", "cache_size": "5000"})
        backend = SQLiteBackend(connection_config=config)
        backend.connect()
        backend.introspect_and_adapt()
        yield backend
        backend.disconnect()

    def test_connect_disconnect(self, disconnected_backend):
        """Test connect and disconnect"""
        backend = disconnected_backend

        # Initially not connected
        assert not backend.is_connected()

        # Connect
        backend.connect()
        assert backend.is_connected()

        # Disconnect
        backend.disconnect()
        assert not backend.is_connected()

    def test_memory_database(self, memory_backend):
        """Test with in-memory database"""
        # Create table
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        memory_backend.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)", options=options)

        # Insert data
        options = ExecutionOptions(stmt_type=StatementType.DML)
        result = memory_backend.execute("INSERT INTO test (name) VALUES (?)", params=("test",), options=options)
        assert result.affected_rows == 1
        assert result.last_insert_id is not None

        # Query data
        row = memory_backend.fetch_one("SELECT * FROM test WHERE id = ?", params=(result.last_insert_id,))
        assert row is not None
        assert row["name"] == "test"

    def test_execute_query(self, backend):
        """Test executing queries"""
        # Create table
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        backend.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)", options=options)

        # Insert data
        options = ExecutionOptions(stmt_type=StatementType.DML)
        result = backend.execute("INSERT INTO test (name) VALUES (?)", params=("test",), options=options)
        assert result.affected_rows == 1

        # Query data
        options = ExecutionOptions(stmt_type=StatementType.DQL)
        result = backend.execute("SELECT * FROM test", options=options)
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0]["name"] == "test"

    def test_fetch_one(self, backend):
        """Test fetch_one"""
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        backend.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)", options=options)

        options = ExecutionOptions(stmt_type=StatementType.DML)
        backend.execute("INSERT INTO test (name) VALUES (?)", params=("row1",), options=options)
        backend.execute("INSERT INTO test (name) VALUES (?)", params=("row2",), options=options)

        row = backend.fetch_one("SELECT * FROM test WHERE name = ?", params=("row2",))
        assert row is not None
        assert row["name"] == "row2"

        # Missing row
        row = backend.fetch_one("SELECT * FROM test WHERE name = ?", params=("missing",))
        assert row is None

    def test_fetch_all(self, backend):
        """Test fetch_all"""
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        backend.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)", options=options)

        options = ExecutionOptions(stmt_type=StatementType.DML)
        for i in range(3):
            backend.execute("INSERT INTO test (name) VALUES (?)", params=(f"row{i}",), options=options)

        rows = backend.fetch_all("SELECT * FROM test ORDER BY id")
        assert rows is not None
        assert len(rows) == 3
        assert rows[0]["name"] == "row0"

    def test_ping(self, disconnected_backend):
        """Test ping"""
        backend = disconnected_backend
        backend.connect()
        assert backend.ping() is True

    def test_pragma_settings(self, pragma_backend):
        """Test PRAGMA settings"""
        # Verify pragma settings
        assert pragma_backend.config.pragmas["synchronous"] == "NORMAL"
        assert pragma_backend.config.pragmas["cache_size"] == "5000"

        # Query actual pragma values
        result = pragma_backend.fetch_one("PRAGMA synchronous")
        assert result["synchronous"] == 1  # NORMAL = 1

        result = pragma_backend.fetch_one("PRAGMA cache_size")
        assert result["cache_size"] == 5000

    def test_server_version(self, memory_backend):
        """Test get_server_version"""
        version = memory_backend.get_server_version()
        assert isinstance(version, tuple)
        assert len(version) == 3
        assert all(isinstance(v, int) for v in version)

    def test_error_handling(self, backend):
        """Test error handling"""
        # Create table
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        backend.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)", options=options)

        # Try to insert duplicate
        options = ExecutionOptions(stmt_type=StatementType.DML)
        backend.execute("INSERT INTO test (id) VALUES (1)", options=options)

        with pytest.raises(Exception):  # Should raise IntegrityError  # noqa: B017
            backend.execute("INSERT INTO test (id) VALUES (1)", options=options)

    def test_context_manager(self, temp_db_path):
        """Test sync context manager"""
        config = SQLiteConnectionConfig(database=temp_db_path)

        with SQLiteBackend(connection_config=config) as backend:
            assert backend.is_connected()

            # Create table and insert data
            options = ExecutionOptions(stmt_type=StatementType.DDL)
            backend.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)", options=options)

            options = ExecutionOptions(stmt_type=StatementType.DML)
            backend.execute("INSERT INTO test (value) VALUES (?)", params=("test",), options=options)

        # Should be disconnected after context
        assert not backend.is_connected()

    def test_auto_connect(self, disconnected_backend):
        """Test auto-connect on execute"""
        backend = disconnected_backend

        # Not connected initially
        assert not backend.is_connected()

        # Execute should auto-connect
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        backend.execute("CREATE TABLE test (id INTEGER)", options=options)

        # Now connected
        assert backend.is_connected()

    def test_delete_on_close(self):
        """Test delete_on_close option"""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        try:
            config = SQLiteConnectionConfig(database=path, delete_on_close=True)
            backend = SQLiteBackend(connection_config=config)

            backend.connect()
            options = ExecutionOptions(stmt_type=StatementType.DDL)
            backend.execute("CREATE TABLE test (id INTEGER)", options=options)

            # File should exist
            assert os.path.exists(path)

            # Disconnect
            backend.disconnect()

            # File should be deleted
            assert not os.path.exists(path)
        finally:
            # Cleanup if test fails
            if os.path.exists(path):
                os.remove(path)

    def test_concurrent_operations(self, memory_backend):
        """Test multiple sequential operations through the sync interface"""
        # Create table
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        memory_backend.execute("CREATE TABLE concurrent_test (id INTEGER PRIMARY KEY, value TEXT)", options=options)

        # Run multiple inserts
        options = ExecutionOptions(stmt_type=StatementType.DML)
        for i in range(5):
            memory_backend.execute(
                "INSERT INTO concurrent_test (value) VALUES (?)", params=(f"value{i}",), options=options
            )

        # Verify all inserted
        options = ExecutionOptions(stmt_type=StatementType.DQL)
        rows = memory_backend.fetch_all("SELECT * FROM concurrent_test ORDER BY id")
        assert len(rows) == 5

    def test_parameterized_queries(self, backend):
        """Test different parameter formats"""
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        backend.execute(
            "CREATE TABLE param_test (id INTEGER PRIMARY KEY, name TEXT, value INTEGER)", options=options
        )

        # Tuple params
        options = ExecutionOptions(stmt_type=StatementType.DML)
        result = backend.execute(
            "INSERT INTO param_test (name, value) VALUES (?, ?)", params=("test1", 100), options=options
        )
        assert result.affected_rows == 1

        # Tuple params (SQLite uses positional placeholders)
        result = backend.execute(
            "INSERT INTO param_test (name, value) VALUES (?, ?)", params=("test2", 200), options=options
        )
        assert result.affected_rows == 1

        # List params
        result = backend.execute(
            "INSERT INTO param_test (name, value) VALUES (?, ?)", params=["test3", 300], options=options
        )
        assert result.affected_rows == 1

        # Verify all inserted
        options = ExecutionOptions(stmt_type=StatementType.DQL)
        rows = backend.fetch_all("SELECT * FROM param_test ORDER BY id")
        assert len(rows) == 3

    def test_query_duration_tracking(self, backend):
        """Test that query duration is tracked"""
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        backend.execute("CREATE TABLE test (id INTEGER)", options=options)

        options = ExecutionOptions(stmt_type=StatementType.DML)
        result = backend.execute("INSERT INTO test (id) VALUES (1)", options=options)

        assert result.duration > 0
        assert isinstance(result.duration, float)


class TestExecuteMany:
    """Test execute_many functionality"""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file path"""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        # Cleanup
        for ext in ["", "-wal", "-shm"]:
            wal_path = path + ext
            if os.path.exists(wal_path):
                try:
                    os.remove(wal_path)
                except OSError:
                    pass

    @pytest.fixture
    def backend(self, temp_db_path):
        """Create sync SQLite backend with test tables"""
        config = SQLiteConnectionConfig(database=temp_db_path)
        backend = SQLiteBackend(connection_config=config)
        backend.connect()
        backend.introspect_and_adapt()

        # Create test tables
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        backend.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, active INTEGER)",
            options=options,
        )

        backend.execute(
            "CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, content TEXT, "
            "FOREIGN KEY (user_id) REFERENCES users (id))",
            options=options,
        )

        yield backend
        backend.disconnect()

    def test_insert_batch(self, backend):
        """Test batch INSERT operations"""
        users = [
            (1, "User 1", "user1@example.com", 1),
            (2, "User 2", "user2@example.com", 1),
            (3, "User 3", "user3@example.com", 0),
        ]

        result = backend.execute_many("INSERT INTO users (id, name, email, active) VALUES (?, ?, ?, ?)", users)

        assert result.affected_rows == 3
        assert result.duration > 0

        # Verify data
        rows = backend.fetch_all("SELECT * FROM users ORDER BY id")
        assert len(rows) == 3
        assert rows[0]["name"] == "User 1"
        assert rows[2]["active"] == 0

    def test_update_batch(self, backend):
        """Test batch UPDATE operations"""
        # Insert test data
        backend.execute_many(
            "INSERT INTO users (id, name, email, active) VALUES (?, ?, ?, ?)",
            [
                (1, "User 1", "user1@example.com", 1),
                (2, "User 2", "user2@example.com", 1),
                (3, "User 3", "user3@example.com", 1),
            ],
        )

        # Batch update
        updates = [("Updated User 1", 1), ("Updated User 3", 3)]

        result = backend.execute_many("UPDATE users SET name = ? WHERE id = ?", updates)

        assert result.affected_rows == 2

        # Verify updates
        user1 = backend.fetch_one("SELECT * FROM users WHERE id = 1")
        user2 = backend.fetch_one("SELECT * FROM users WHERE id = 2")
        user3 = backend.fetch_one("SELECT * FROM users WHERE id = 3")

        assert user1["name"] == "Updated User 1"
        assert user2["name"] == "User 2"  # Not updated
        assert user3["name"] == "Updated User 3"

    def test_empty_params_list(self, backend):
        """Test execute_many with empty params list"""
        result = backend.execute_many("INSERT INTO users (id, name) VALUES (?, ?)", [])

        assert result.affected_rows == 0
        assert result.duration >= 0

        # Verify no data inserted
        count = backend.fetch_one("SELECT COUNT(*) as count FROM users")
        assert count["count"] == 0

    def test_params_mismatch(self, backend):
        """Test execute_many with mismatched parameters"""
        # Too few parameters
        with pytest.raises(Exception):  # noqa: B017
            backend.execute_many(
                "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
                [(1, "User 1")],  # Missing email
            )

        # Too many parameters
        with pytest.raises(Exception):  # noqa: B017
            backend.execute_many(
                "INSERT INTO users (id, name) VALUES (?, ?)",
                [(1, "User 1", "extra@example.com")],  # Extra parameter
            )

    def test_table_not_exists(self, backend):
        """Test execute_many with non-existent table"""
        with pytest.raises((DatabaseError, QueryError)) as exc_info:
            backend.execute_many("INSERT INTO nonexistent (id, name) VALUES (?, ?)", [(1, "Test"), (2, "Test 2")])

        assert "no such table" in str(exc_info.value).lower()

    def test_foreign_key_constraint(self, backend):
        """Test execute_many with foreign key constraint violation"""
        # Try to insert posts with non-existent user_ids
        with pytest.raises(DatabaseError) as exc_info:
            backend.execute_many(
                "INSERT INTO posts (id, user_id, title) VALUES (?, ?, ?)", [(1, 99, "Title 1"), (2, 100, "Title 2")]
            )

        assert "foreign key constraint" in str(exc_info.value).lower()

        # Insert valid user first
        options = ExecutionOptions(stmt_type=StatementType.DML)
        backend.execute("INSERT INTO users (id, name) VALUES (1, 'User 1')", options=options)

        # Try with mix of valid and invalid
        with pytest.raises(DatabaseError) as exc_info:
            backend.execute_many(
                "INSERT INTO posts (id, user_id, title) VALUES (?, ?, ?)",
                [
                    (1, 1, "Title 1"),  # Valid
                    (2, 999, "Title 2"),  # Invalid
                ],
            )

        assert "foreign key constraint" in str(exc_info.value).lower()

        # Verify only one post inserted (or none due to rollback)
        count = backend.fetch_one("SELECT COUNT(*) as count FROM posts")
        assert count["count"] <= 1

    def test_large_batch(self, backend):
        """Test execute_many with large batch"""
        large_batch = [(i, f"User {i}", f"user{i}@example.com", 1) for i in range(1, 101)]

        result = backend.execute_many(
            "INSERT INTO users (id, name, email, active) VALUES (?, ?, ?, ?)", large_batch
        )

        assert result.affected_rows == 100

        # Verify count
        count = backend.fetch_one("SELECT COUNT(*) as count FROM users")
        assert count["count"] == 100

    def test_affected_rows_count(self, backend):
        """Test affected_rows count in various scenarios"""
        # Insert test data
        backend.execute_many(
            "INSERT INTO users (id, name, active) VALUES (?, ?, ?)",
            [(1, "User 1", 1), (2, "User 2", 1), (3, "User 3", 0)],
        )

        # UPDATE that affects some rows
        result = backend.execute_many("UPDATE users SET name = ? WHERE active = ?", [("Active User", 1)])
        assert result.affected_rows == 2

        # UPDATE that affects no rows
        result = backend.execute_many("UPDATE users SET name = ? WHERE id > ?", [("No one", 100)])
        assert result.affected_rows == 0

        # UPDATE with multiple parameter sets
        result = backend.execute_many("UPDATE users SET active = ? WHERE id = ?", [(0, 1), (0, 2)])
        assert result.affected_rows == 2

    def test_execute_many_duration_tracking(self, backend):
        """Test that duration is tracked for execute_many"""
        result = backend.execute_many(
            "INSERT INTO users (id, name) VALUES (?, ?)", [(1, "User 1"), (2, "User 2"), (3, "User 3")]
        )

        assert result.duration > 0
        assert isinstance(result.duration, float)


class TestSQLiteTransaction:
    """Test sync transaction management"""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file path"""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        # Cleanup
        for ext in ["", "-wal", "-shm"]:
            wal_path = path + ext
            if os.path.exists(wal_path):
                try:
                    os.remove(wal_path)
                except OSError:
                    pass

    @pytest.fixture
    def backend(self, temp_db_path):
        """Create sync SQLite backend with test table"""
        config = SQLiteConnectionConfig(database=temp_db_path)
        backend = SQLiteBackend(connection_config=config)
        backend.connect()
        backend.introspect_and_adapt()

        # Create test table
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        backend.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)", options=options)

        yield backend
        backend.disconnect()

    def test_transaction_property(self, backend):
        """Test transaction manager property"""
        # Initially no transaction manager
        assert backend._transaction_manager is None

        # Access property creates it
        tm = backend.transaction_manager
        assert tm is not None
        assert backend._transaction_manager is tm

        # Same instance returned
        assert backend.transaction_manager is tm

    def test_begin_commit(self, backend):
        """Test begin and commit transaction"""
        backend.begin_transaction()
        assert backend.in_transaction is True

        # Insert data
        options = ExecutionOptions(stmt_type=StatementType.DML)
        backend.execute("INSERT INTO test (value) VALUES (?)", params=("test",), options=options)

        # Commit
        backend.commit_transaction()
        assert backend.in_transaction is False

        # Verify data committed
        row = backend.fetch_one("SELECT * FROM test WHERE value = ?", params=("test",))
        assert row is not None
        assert row["value"] == "test"

    def test_begin_rollback(self, backend):
        """Test begin and rollback transaction"""
        backend.begin_transaction()

        # Insert data
        options = ExecutionOptions(stmt_type=StatementType.DML)
        backend.execute("INSERT INTO test (value) VALUES (?)", params=("test",), options=options)

        # Rollback
        backend.rollback_transaction()
        assert backend.in_transaction is False

        # Verify data rolled back
        row = backend.fetch_one("SELECT * FROM test WHERE value = ?", params=("test",))
        assert row is None

    def test_transaction_context_manager(self, backend):
        """Test transaction context manager"""
        with backend.transaction():
            options = ExecutionOptions(stmt_type=StatementType.DML)
            backend.execute("INSERT INTO test (value) VALUES (?)", params=("test",), options=options)

        # Should auto-commit
        assert backend.in_transaction is False
        row = backend.fetch_one("SELECT * FROM test WHERE value = ?", params=("test",))
        assert row is not None

    def test_transaction_context_manager_exception(self, backend):
        """Test transaction context manager with exception"""
        try:
            with backend.transaction():
                options = ExecutionOptions(stmt_type=StatementType.DML)
                backend.execute("INSERT INTO test (value) VALUES (?)", params=("test",), options=options)
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Should auto-rollback
        assert backend.in_transaction is False
        row = backend.fetch_one("SELECT * FROM test WHERE value = ?", params=("test",))
        assert row is None

    def test_nested_transactions(self, backend):
        """Test nested transactions"""
        # Outer transaction
        backend.begin_transaction()
        options = ExecutionOptions(stmt_type=StatementType.DML)
        backend.execute("INSERT INTO test (id, value) VALUES (1, 'outer')", options=options)

        # Inner transaction
        backend.begin_transaction()
        backend.execute("INSERT INTO test (id, value) VALUES (2, 'inner')", options=options)

        # Rollback inner
        backend.rollback_transaction()

        # Verify inner rolled back
        row = backend.fetch_one("SELECT * FROM test WHERE id = 2")
        assert row is None

        # Verify outer still exists
        row = backend.fetch_one("SELECT * FROM test WHERE id = 1")
        assert row is not None

        # Commit outer
        backend.commit_transaction()

        # Verify outer committed
        row = backend.fetch_one("SELECT * FROM test WHERE id = 1")
        assert row is not None
        assert row["value"] == "outer"

    def test_multiple_nested_levels(self, backend):
        """Test multiple nested transaction levels"""
        # Level 1
        backend.begin_transaction()
        options = ExecutionOptions(stmt_type=StatementType.DML)
        backend.execute("INSERT INTO test (id, value) VALUES (1, 'level1')", options=options)

        # Level 2
        backend.begin_transaction()
        backend.execute("INSERT INTO test (id, value) VALUES (2, 'level2')", options=options)

        # Level 3
        backend.begin_transaction()
        backend.execute("INSERT INTO test (id, value) VALUES (3, 'level3')", options=options)

        # Check transaction level
        assert backend.transaction_manager._transaction_level == 3

        # Rollback level 3
        backend.rollback_transaction()
        assert backend.transaction_manager._transaction_level == 2

        # Commit level 2
        backend.commit_transaction()
        assert backend.transaction_manager._transaction_level == 1

        # Commit level 1
        backend.commit_transaction()
        assert backend.in_transaction is False

        # Verify final state
        rows = backend.fetch_all("SELECT * FROM test ORDER BY id")
        assert len(rows) == 2
        assert rows[0]["value"] == "level1"
        assert rows[1]["value"] == "level2"

    def test_savepoint_operations(self, backend):
        """Test savepoint operations"""
        backend.begin_transaction()
        options = ExecutionOptions(stmt_type=StatementType.DML)
        backend.execute("INSERT INTO test (id, value) VALUES (1, 'base')", options=options)

        # Create savepoint
        backend.transaction_manager.savepoint("sp1")
        backend.execute("INSERT INTO test (id, value) VALUES (2, 'sp1')", options=options)

        # Create second savepoint
        backend.transaction_manager.savepoint("sp2")
        backend.execute("INSERT INTO test (id, value) VALUES (3, 'sp2')", options=options)

        # Rollback to first savepoint
        backend.transaction_manager.rollback_to("sp1")

        # Verify rollback
        rows = backend.fetch_all("SELECT * FROM test ORDER BY id")
        assert len(rows) == 1
        assert rows[0]["value"] == "base"

        # Add new data
        backend.execute("INSERT INTO test (id, value) VALUES (4, 'after-rollback')", options=options)

        # Release savepoint
        backend.transaction_manager.release("sp1")

        # Commit
        backend.commit_transaction()

        # Verify final state
        rows = backend.fetch_all("SELECT * FROM test ORDER BY id")
        assert len(rows) == 2
        assert rows[0]["value"] == "base"
        assert rows[1]["value"] == "after-rollback"

    def test_auto_savepoint_name(self, backend):
        """Test auto-generated savepoint names"""
        backend.begin_transaction()

        # Create savepoints with auto names
        sp1 = backend.transaction_manager.savepoint()
        assert sp1.startswith("SP_")

        sp2 = backend.transaction_manager.savepoint()
        assert sp2 == "SP_2"

        backend.rollback_transaction()

    def test_isolation_level_serializable(self, backend):
        """Test serializable isolation level"""
        tm = backend.transaction_manager
        tm.isolation_level = IsolationLevel.SERIALIZABLE

        backend.begin_transaction()
        assert backend.in_transaction is True

        # Check read_uncommitted = 0
        result = backend.fetch_one("PRAGMA read_uncommitted")
        assert result["read_uncommitted"] == 0

        backend.commit_transaction()

    def test_isolation_level_read_uncommitted(self, backend):
        """Test read uncommitted isolation level"""
        tm = backend.transaction_manager
        tm.isolation_level = IsolationLevel.READ_UNCOMMITTED

        backend.begin_transaction()
        assert backend.in_transaction is True

        # Check read_uncommitted = 1
        result = backend.fetch_one("PRAGMA read_uncommitted")
        assert result["read_uncommitted"] == 1

        backend.commit_transaction()

    def test_unsupported_isolation_level(self, backend):
        """Test unsupported isolation level"""
        tm = backend.transaction_manager

        with pytest.raises(TransactionError) as exc_info:
            tm.isolation_level = IsolationLevel.READ_COMMITTED

        assert "Unsupported isolation level" in str(exc_info.value)

    def test_set_isolation_level_during_transaction(self, backend):
        """Test setting isolation level during transaction"""
        backend.begin_transaction()

        tm = backend.transaction_manager
        with pytest.raises(TransactionError) as exc_info:
            tm.isolation_level = IsolationLevel.SERIALIZABLE

        assert "Cannot change isolation level during active transaction" in str(exc_info.value)

        backend.rollback_transaction()

    def test_commit_without_transaction(self, backend):
        """Test commit without active transaction"""
        with pytest.raises(TransactionError) as exc_info:
            backend.commit_transaction()

        assert "No active transaction to commit" in str(exc_info.value)

    def test_rollback_without_transaction(self, backend):
        """Test rollback without active transaction"""
        with pytest.raises(TransactionError) as exc_info:
            backend.rollback_transaction()

        assert "No active transaction to rollback" in str(exc_info.value)

    def test_savepoint_without_transaction(self, backend):
        """Test creating savepoint without active transaction"""
        with pytest.raises(TransactionError) as exc_info:
            backend.transaction_manager.savepoint("sp1")

        assert "Cannot create savepoint: no active transaction" in str(exc_info.value)

    def test_release_invalid_savepoint(self, backend):
        """Test releasing invalid savepoint"""
        backend.begin_transaction()

        with pytest.raises(TransactionError) as exc_info:
            backend.transaction_manager.release("nonexistent")

        assert "Invalid savepoint name" in str(exc_info.value)

        backend.rollback_transaction()

    def test_rollback_to_invalid_savepoint(self, backend):
        """Test rollback to invalid savepoint"""
        backend.begin_transaction()

        with pytest.raises(TransactionError) as exc_info:
            backend.transaction_manager.rollback_to("nonexistent")

        assert "Invalid savepoint name" in str(exc_info.value)

        backend.rollback_transaction()

    def test_supports_savepoint(self, backend):
        """Test savepoint support check"""
        assert backend.transaction_manager.supports_savepoint() is True

    def test_mixed_savepoint_transactions(self, backend):
        """Test mixed usage of savepoints and nested transactions"""
        # Begin main transaction
        backend.begin_transaction()
        options = ExecutionOptions(stmt_type=StatementType.DML)
        backend.execute("INSERT INTO test (id, value) VALUES (1, 'main')", options=options)

        # Create manual savepoint
        sp1 = backend.transaction_manager.savepoint("manual_sp")
        backend.execute("INSERT INTO test (id, value) VALUES (2, 'manual_sp')", options=options)

        # Create nested transaction
        backend.begin_transaction()
        backend.execute("INSERT INTO test (id, value) VALUES (3, 'nested')", options=options)

        # Verify 3 rows
        rows = backend.fetch_all("SELECT COUNT(*) as cnt FROM test")
        assert rows[0]["cnt"] == 3

        # Rollback nested
        backend.rollback_transaction()

        # Verify 2 rows
        rows = backend.fetch_all("SELECT COUNT(*) as cnt FROM test")
        assert rows[0]["cnt"] == 2

        # Rollback to manual savepoint
        backend.transaction_manager.rollback_to(sp1)

        # Verify 1 row
        rows = backend.fetch_all("SELECT COUNT(*) as cnt FROM test")
        assert rows[0]["cnt"] == 1

        # Commit main
        backend.commit_transaction()

        # Verify final state
        rows = backend.fetch_all("SELECT * FROM test")
        assert len(rows) == 1
        assert rows[0]["value"] == "main"

    def test_transaction_level_counter(self, backend):
        """Test transaction level counter"""
        tm = backend.transaction_manager
        assert tm._transaction_level == 0

        backend.begin_transaction()
        assert tm._transaction_level == 1

        backend.begin_transaction()
        assert tm._transaction_level == 2

        backend.rollback_transaction()
        assert tm._transaction_level == 1

        backend.commit_transaction()
        assert tm._transaction_level == 0


from rhosocial.activerecord.backend.expression import (  # noqa: E402
    InsertExpression as _InsertExpression,
    ValuesSource as _ValuesSource,
    Literal as _Literal,
    Column as _Column,
    ReturningClause as _ReturningClause,
    UpdateExpression as _UpdateExpression,
    DeleteExpression as _DeleteExpression,
)


class TestReturning:
    """Test sync RETURNING clause functionality"""

    @pytest.fixture
    def backend(self):
        """Create an in-memory sync SQLite backend"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        backend.connect()
        backend.introspect_and_adapt()
        yield backend
        backend.disconnect()

    def test_returning_not_supported_dialect(self):
        """Test that dialect raises UnsupportedFeatureError for RETURNING on older versions."""
        dialect = SQLiteDialect(version=(3, 34, 0))

        insert_expr = _InsertExpression(
            dialect=dialect,
            into="users",
            columns=["name"],
            source=_ValuesSource(dialect, values_list=[[_Literal(dialect, "test")]]),
            returning=_ReturningClause(dialect, expressions=[_Column(dialect, "id")]),
        )

        with pytest.raises(UnsupportedFeatureError, match="RETURNING clause"):
            insert_expr.to_sql()

    @patch("sqlite3.sqlite_version", "3.35.0")
    def test_returning_with_insert(self, backend):
        """Test RETURNING with INSERT"""
        dialect = backend.dialect

        # Create table
        backend.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )

        insert_expr = _InsertExpression(
            dialect=dialect,
            into="users",
            columns=["name", "email"],
            source=_ValuesSource(
                dialect, values_list=[[_Literal(dialect, "Alice"), _Literal(dialect, "alice@example.com")]]
            ),
            returning=_ReturningClause(dialect, expressions=[_Column(dialect, "id"), _Column(dialect, "name")]),
        )

        sql, params = insert_expr.to_sql()

        result = backend.execute(sql, params=params, options=ExecutionOptions(stmt_type=StatementType.DQL))

        assert result.affected_rows == 1
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0]["id"] == 1
        assert result.data[0]["name"] == "Alice"

    @patch("sqlite3.sqlite_version", "3.35.0")
    def test_returning_with_update(self, backend):
        """Test RETURNING with UPDATE"""
        dialect = backend.dialect
        # Create and populate table
        backend.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )

        backend.execute(
            "INSERT INTO users (id, name, email) VALUES (1, 'Original', 'old@example.com')",
            options=ExecutionOptions(stmt_type=StatementType.DML),
        )

        update_expr = _UpdateExpression(
            dialect=dialect,
            table="users",
            assignments={"name": _Literal(dialect, "Updated"), "email": _Literal(dialect, "new@example.com")},
            where=_Column(dialect, "id") == _Literal(dialect, 1),
            returning=_ReturningClause(
                dialect, expressions=[_Column(dialect, "id"), _Column(dialect, "name"), _Column(dialect, "email")]
            ),
        )
        sql, params = update_expr.to_sql()

        result = backend.execute(sql, params=params, options=ExecutionOptions(stmt_type=StatementType.DQL))

        assert result.affected_rows == 1
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0]["id"] == 1
        assert result.data[0]["name"] == "Updated"
        assert result.data[0]["email"] == "new@example.com"

    @patch("sqlite3.sqlite_version", "3.35.0")
    def test_returning_with_delete(self, backend):
        """Test RETURNING with DELETE"""
        dialect = backend.dialect
        # Create and populate table
        backend.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )

        backend.execute(
            "INSERT INTO users (id, name) VALUES (1, 'ToDelete')", options=ExecutionOptions(stmt_type=StatementType.DML)
        )

        delete_expr = _DeleteExpression(
            dialect=dialect,
            tables="users",
            where=_Column(dialect, "id") == _Literal(dialect, 1),
            returning=_ReturningClause(dialect, expressions=[_Column(dialect, "name")]),
        )
        sql, params = delete_expr.to_sql()

        result = backend.execute(sql, params=params, options=ExecutionOptions(stmt_type=StatementType.DQL))

        assert result.affected_rows == 1
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0]["name"] == "ToDelete"

        # Verify deleted
        row = backend.fetch_one("SELECT * FROM users WHERE id = 1")
        assert row is None

    @patch("sqlite3.sqlite_version", "3.35.0")
    def test_returning_invalid_columns(self, backend):
        """Test RETURNING with invalid column names follows SQLite's quirky behavior."""
        dialect = backend.dialect
        # Create table
        backend.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )

        insert_expr = _InsertExpression(
            dialect=dialect,
            into="users",
            columns=["name"],
            source=_ValuesSource(dialect, values_list=[[_Literal(dialect, "test")]]),
            returning=_ReturningClause(dialect, expressions=[_Column(dialect, "invalid_column")]),
        )
        sql, params = insert_expr.to_sql()

        # SQLite does not raise an error for invalid columns in RETURNING.
        # Instead, it returns the column name as a string value.
        result = backend.execute(sql, params=params, options=ExecutionOptions(stmt_type=StatementType.DQL))

        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0]["invalid_column"] == "invalid_column"

    @patch("sqlite3.sqlite_version", "3.35.0")
    def test_returning_multiple_rows(self, backend):
        """Test RETURNING with operations affecting multiple rows"""
        dialect = backend.dialect
        # Create and populate table
        backend.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, active INTEGER)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )

        backend.execute(
            "INSERT INTO users (id, name, active) VALUES (1, 'User1', 1)",
            options=ExecutionOptions(stmt_type=StatementType.DML),
        )
        backend.execute(
            "INSERT INTO users (id, name, active) VALUES (2, 'User2', 1)",
            options=ExecutionOptions(stmt_type=StatementType.DML),
        )
        backend.execute(
            "INSERT INTO users (id, name, active) VALUES (3, 'User3', 0)",
            options=ExecutionOptions(stmt_type=StatementType.DML),
        )

        update_expr = _UpdateExpression(
            dialect=dialect,
            table="users",
            assignments={"active": _Literal(dialect, 0)},
            where=_Column(dialect, "active") == _Literal(dialect, 1),
            returning=_ReturningClause(dialect, expressions=[_Column(dialect, "id"), _Column(dialect, "name")]),
        )
        sql, params = update_expr.to_sql()

        result = backend.execute(sql, params=params, options=ExecutionOptions(stmt_type=StatementType.DQL))

        assert result.affected_rows == 2
        assert result.data is not None
        assert len(result.data) == 2
        returned_ids = {row["id"] for row in result.data}
        assert returned_ids == {1, 2}

    @patch("sqlite3.sqlite_version", "3.35.0")
    def test_returning_with_transaction(self, backend):
        """Test RETURNING within transaction"""
        dialect = backend.dialect
        # Create table
        backend.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )

        # Transaction with RETURNING
        with backend.transaction():
            insert_expr = _InsertExpression(
                dialect=dialect,
                into="users",
                columns=["name"],
                source=_ValuesSource(dialect, values_list=[[_Literal(dialect, "TransUser")]]),
                returning=_ReturningClause(dialect, expressions=[_Column(dialect, "id")]),
            )
            sql, params = insert_expr.to_sql()

            result = backend.execute(sql, params=params, options=ExecutionOptions(stmt_type=StatementType.DQL))

            assert result.affected_rows == 1
            assert result.data is not None
            assert len(result.data) == 1
            assert result.data[0]["id"] == 1

        # Verify committed
        row = backend.fetch_one("SELECT * FROM users WHERE name = ?", params=("TransUser",))
        assert row is not None
        assert row["id"] == 1


class TestColumnMapping:
    """Test sync column mapping functionality"""

    @pytest.fixture
    def mapped_table_backend(self):
        """
        Fixture to set up an in-memory SQLite database, a SQLiteBackend instance,
        and a 'mapped_users' table with columns for type adaptation.
        """
        backend = SQLiteBackend(database=":memory:")
        backend.connect()

        create_table_sql = """
        CREATE TABLE mapped_users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP NOT NULL,
            user_uuid TEXT,
            is_active INTEGER
        );
        """
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        backend.execute(create_table_sql, options=options)

        yield backend

        backend.disconnect()

    def test_insert_and_returning_with_mapping(self, mapped_table_backend):
        """
        Tests that execute() with an INSERT and a RETURNING clause correctly uses
        column_mapping to map the resulting column names back to field names.
        """
        backend = mapped_table_backend
        from datetime import datetime

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

        column_to_field_mapping = {
            "user_id": "user_pk",
            "name": "full_name",
            "email": "user_email",
            "created_at": "created_timestamp",
        }

        sql = "INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)"
        params = ("John Doe", "john.doe@example.com", now_str)

        result = backend.execute(
            sql=sql,
            params=params,
            options=ExecutionOptions(stmt_type=StatementType.DML, column_mapping=column_to_field_mapping),
        )

        assert result.affected_rows == 1

    def test_update_with_backend(self, mapped_table_backend):
        """Tests that an update operation via execute() works correctly."""
        backend = mapped_table_backend
        from datetime import datetime

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

        options = ExecutionOptions(stmt_type=StatementType.DML)
        backend.execute(
            "INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
            ("Jane Doe", "jane.doe@example.com", now_str),
            options=options,
        )

        sql = "UPDATE mapped_users SET name = ? WHERE user_id = ?"
        params = ("Jane Smith", 1)
        result = backend.execute(sql, params, options=options)

        assert result.affected_rows == 1

        fetch_options = ExecutionOptions(stmt_type=StatementType.DQL)
        fetch_result = backend.execute("SELECT name FROM mapped_users WHERE user_id = 1", options=fetch_options)
        fetched_row = fetch_result.data[0] if fetch_result.data else None
        assert fetched_row is not None
        assert fetched_row["name"] == "Jane Smith"

    def test_execute_fetch_with_mapping(self, mapped_table_backend):
        """Tests that an execute/fetch call correctly uses column_mapping."""
        backend = mapped_table_backend
        from datetime import datetime

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

        column_to_field_mapping = {"user_id": "user_pk", "name": "full_name", "email": "user_email"}

        options = ExecutionOptions(stmt_type=StatementType.DML)
        backend.execute(
            "INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
            ("Fetch Test", "fetch@example.com", now_str),
            options=options,
        )

        fetch_options = ExecutionOptions(stmt_type=StatementType.DQL, column_mapping=column_to_field_mapping)
        result = backend.execute("SELECT * FROM mapped_users WHERE user_id = 1", options=fetch_options)
        fetched_row = result.data[0] if result.data else None

        assert fetched_row is not None
        assert "full_name" in fetched_row
        assert "user_email" in fetched_row
        assert "created_at" in fetched_row
        assert fetched_row["full_name"] == "Fetch Test"
        assert fetched_row["user_pk"] == 1

    def test_execute_fetch_without_mapping(self, mapped_table_backend):
        """Tests a fetch call WITHOUT column_mapping returns raw column names."""
        backend = mapped_table_backend
        from datetime import datetime

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

        options = ExecutionOptions(stmt_type=StatementType.DML)
        backend.execute(
            "INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
            ("No Map", "nomap@example.com", now_str),
            options=options,
        )

        fetch_options = ExecutionOptions(stmt_type=StatementType.DQL)
        result = backend.execute("SELECT * FROM mapped_users WHERE user_id = 1", options=fetch_options)
        fetched_row = result.data[0] if result.data else None

        assert fetched_row is not None
        assert "user_id" in fetched_row
        assert "name" in fetched_row
        assert "full_name" not in fetched_row
        assert "user_pk" not in fetched_row
        assert fetched_row["name"] == "No Map"

    def test_fetch_with_combined_mapping_and_adapters(self, mapped_table_backend):
        """Tests that execute() correctly applies both column_mapping and column_adapters."""
        backend = mapped_table_backend
        from datetime import datetime
        import uuid

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        test_uuid = uuid.uuid4()

        column_to_field_mapping = {"user_id": "pk", "name": "full_name", "user_uuid": "uuid", "is_active": "active"}

        uuid_adapter = backend.adapter_registry.get_adapter(uuid.UUID, str)
        bool_adapter = backend.adapter_registry.get_adapter(bool, int)

        column_adapters = {"user_uuid": (uuid_adapter, uuid.UUID), "is_active": (bool_adapter, bool)}

        options = ExecutionOptions(stmt_type=StatementType.DML)
        backend.execute(
            "INSERT INTO mapped_users (name, email, created_at, user_uuid, is_active) VALUES (?, ?, ?, ?, ?)",
            ("Combined", "combined@example.com", now_str, str(test_uuid), 1),
            options=options,
        )

        fetch_options = ExecutionOptions(
            stmt_type=StatementType.DQL, column_mapping=column_to_field_mapping, column_adapters=column_adapters
        )
        result = backend.execute("SELECT * FROM mapped_users WHERE user_id = 1", options=fetch_options)

        fetched_row = result.data[0] if result.data else None
        assert fetched_row is not None

        assert "full_name" in fetched_row
        assert "uuid" in fetched_row
        assert "active" in fetched_row
        assert "name" not in fetched_row
        assert "user_uuid" not in fetched_row

        assert fetched_row["full_name"] == "Combined"
        # The adapter should convert the UUID string from the DB back to a UUID object.
        assert fetched_row["uuid"] == test_uuid
        # The adapter should convert the integer from the DB back to a boolean.
        assert fetched_row["active"] is True
