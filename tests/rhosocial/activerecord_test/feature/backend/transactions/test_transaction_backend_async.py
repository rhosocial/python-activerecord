# tests/rhosocial/activerecord_test/feature/backend/transactions/test_transaction_backend_async.py
"""Async twin of test_transaction_backend.py: AsyncSQLiteBackend transaction lifecycle."""

import os
import tempfile

import pytest
import pytest_asyncio

from rhosocial.activerecord.backend.errors import IntegrityError
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.async_transaction import AsyncSQLiteTransactionManager
from rhosocial.activerecord.backend.config import ConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions, InsertOptions, UpdateOptions, DeleteOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.expression import Column, Literal, ComparisonPredicate


class TestAsyncSQLiteBackendTransaction:
    """Async transaction lifecycle twin of TestSQLiteBackendTransaction."""

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
                    os.unlink(wal_path)
                except OSError as e:
                    print(f"Warning: Failed to delete file {wal_path}: {e}")

    @pytest.fixture
    def config(self, temp_db_path):
        """Create database configuration"""
        return ConnectionConfig(database=temp_db_path)

    @pytest_asyncio.fixture
    async def backend(self, config):
        """Create AsyncSQLiteBackend with a test table"""
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()
        await backend.execute(
            "CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, value TEXT)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        return backend

    @pytest.mark.asyncio
    async def test_transaction_property(self, backend):
        """Test transaction manager property"""
        assert backend._transaction_manager is None

        assert isinstance(backend.transaction_manager, AsyncSQLiteTransactionManager)
        assert backend._transaction_manager is not None

        assert backend.transaction_manager is backend._transaction_manager

    @pytest.mark.asyncio
    async def test_begin_transaction(self, backend):
        """Test beginning a transaction"""
        await backend.begin_transaction()
        assert backend.in_transaction is True
        assert backend.transaction_manager.is_active is True

    @pytest.mark.asyncio
    async def test_commit_transaction(self, backend):
        """Test committing a transaction"""
        await backend.begin_transaction()

        await backend.execute(
            "INSERT INTO test (id, value) VALUES (1, 'test commit')",
            (),
            options=ExecutionOptions(stmt_type=StatementType.INSERT),
        )

        await backend.commit_transaction()
        assert backend.in_transaction is False

        result = await backend.fetch_one("SELECT * FROM test WHERE id = 1")
        assert result is not None
        assert result["id"] == 1
        assert result["value"] == "test commit"

    @pytest.mark.asyncio
    async def test_rollback_transaction(self, backend):
        """Test rolling back a transaction"""
        await backend.begin_transaction()

        await backend.execute(
            "INSERT INTO test (id, value) VALUES (2, 'test rollback')",
            (),
            options=ExecutionOptions(stmt_type=StatementType.INSERT),
        )

        await backend.rollback_transaction()
        assert backend.in_transaction is False

        result = await backend.fetch_one("SELECT * FROM test WHERE id = 2")
        assert result is None

    @pytest.mark.asyncio
    async def test_transaction_context_manager(self, backend):
        """Test transaction context manager"""
        async with backend.transaction():
            await backend.execute(
                "INSERT INTO test (id, value) VALUES (3, 'context manager')",
                (),
                options=ExecutionOptions(stmt_type=StatementType.INSERT),
            )

        assert backend.in_transaction is False
        result = await backend.fetch_one("SELECT * FROM test WHERE id = 3")
        assert result is not None
        assert result["id"] == 3
        assert result["value"] == "context manager"

    @pytest.mark.asyncio
    async def test_transaction_context_manager_exception(self, backend):
        """Test transaction context manager exception handling"""
        try:
            async with backend.transaction():
                await backend.execute(
                    "INSERT INTO test (id, value) VALUES (4, 'context exception')",
                    (),
                    options=ExecutionOptions(stmt_type=StatementType.INSERT),
                )
                raise ValueError("Test exception")
        except ValueError:
            pass

        assert backend.in_transaction is False
        result = await backend.fetch_one("SELECT * FROM test WHERE id = 4")
        assert result is None

    @pytest.mark.asyncio
    async def test_nested_transactions(self, backend):
        """Test nested transactions"""
        await backend.begin_transaction()

        await backend.execute(
            "INSERT INTO test (id, value) VALUES (5, 'outer')",
            (),
            options=ExecutionOptions(stmt_type=StatementType.INSERT),
        )

        await backend.begin_transaction()

        await backend.execute(
            "INSERT INTO test (id, value) VALUES (6, 'inner')",
            (),
            options=ExecutionOptions(stmt_type=StatementType.INSERT),
        )

        await backend.rollback_transaction()

        result = await backend.fetch_one("SELECT * FROM test WHERE id = 6")
        assert result is None

        result = await backend.fetch_one("SELECT * FROM test WHERE id = 5")
        assert result is not None
        assert result["value"] == "outer"

        await backend.commit_transaction()

        result = await backend.fetch_one("SELECT * FROM test WHERE id = 5")
        assert result is not None
        assert result["value"] == "outer"

    @pytest.mark.asyncio
    async def test_mixed_nested_transactions(self, backend):
        """Test mixed nested transactions (including context manager)"""
        await backend.begin_transaction()

        await backend.execute(
            "INSERT INTO test (id, value) VALUES (7, 'outer mixed')",
            (),
            options=ExecutionOptions(stmt_type=StatementType.INSERT),
        )

        async with backend.transaction():
            await backend.execute(
                "INSERT INTO test (id, value) VALUES (8, 'inner mixed')",
                (),
                options=ExecutionOptions(stmt_type=StatementType.INSERT),
            )

        result = await backend.fetch_all("SELECT * FROM test WHERE id IN (7, 8) ORDER BY id")
        assert len(result) == 2
        assert result[0]["value"] == "outer mixed"
        assert result[1]["value"] == "inner mixed"

        await backend.rollback_transaction()

        result = await backend.fetch_all("SELECT * FROM test WHERE id IN (7, 8)")
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_auto_transaction_on_insert(self, backend):
        """Test automatic transaction handling for insert operations"""
        insert_opts = InsertOptions(table="test", data={"id": 9, "value": "auto insert"}, primary_key="id")
        result = await backend.insert(insert_opts)

        assert result.affected_rows == 1

        row = await backend.fetch_one("SELECT * FROM test WHERE id = 9")
        assert row is not None
        assert row["value"] == "auto insert"

    @pytest.mark.asyncio
    async def test_auto_transaction_on_update(self, backend):
        """Test automatic transaction handling for update operations"""
        insert_opts = InsertOptions(table="test", data={"id": 10, "value": "before update"}, primary_key="id")
        await backend.insert(insert_opts)

        where_clause = ComparisonPredicate(
            backend.dialect, "=", Column(backend.dialect, "id"), Literal(backend.dialect, 10)
        )
        update_opts = UpdateOptions(table="test", data={"value": "after update"}, where=where_clause)
        result = await backend.update(update_opts)

        assert result.affected_rows == 1

        row = await backend.fetch_one("SELECT * FROM test WHERE id = 10")
        assert row is not None
        assert row["value"] == "after update"

    @pytest.mark.asyncio
    async def test_auto_transaction_on_delete(self, backend):
        """Test automatic transaction handling for delete operations"""
        insert_opts = InsertOptions(table="test", data={"id": 11, "value": "to be deleted"}, primary_key="id")
        await backend.insert(insert_opts)

        row = await backend.fetch_one("SELECT * FROM test WHERE id = 11")
        assert row is not None

        where_clause = ComparisonPredicate(
            backend.dialect, "=", Column(backend.dialect, "id"), Literal(backend.dialect, 11)
        )
        delete_opts = DeleteOptions(table="test", where=where_clause)
        result = await backend.delete(delete_opts)

        assert result.affected_rows == 1

        row = await backend.fetch_one("SELECT * FROM test WHERE id = 11")
        assert row is None

    @pytest.mark.asyncio
    async def test_transaction_with_integrity_error(self, backend):
        """Test integrity error within a transaction"""
        insert_opts = InsertOptions(table="test", data={"id": 12, "value": "unique"}, primary_key="id")
        await backend.insert(insert_opts)

        await backend.begin_transaction()

        await backend.execute(
            "INSERT INTO test (id, value) VALUES (13, 'before error')",
            (),
            options=ExecutionOptions(stmt_type=StatementType.INSERT),
        )

        with pytest.raises(IntegrityError):
            await backend.execute(
                "INSERT INTO test (id, value) VALUES (12, 'duplicate')",
                (),
                options=ExecutionOptions(stmt_type=StatementType.INSERT),
            )

        await backend.rollback_transaction()

        row = await backend.fetch_one("SELECT * FROM test WHERE id = 13")
        assert row is None

    @pytest.mark.asyncio
    async def test_connection_context_manager(self, backend):
        """Test connection context manager"""
        async with backend as conn:
            await conn.execute(
                "INSERT INTO test (id, value) VALUES (14, 'connection context')",
                (),
                options=ExecutionOptions(stmt_type=StatementType.INSERT),
            )

        row = await backend.fetch_one("SELECT * FROM test WHERE id = 14")
        assert row is not None
        assert row["value"] == "connection context"

    @pytest.mark.asyncio
    async def test_disconnect_during_transaction(self, backend):
        """Test disconnecting during a transaction"""
        await backend.begin_transaction()

        await backend.execute(
            "INSERT INTO test (id, value) VALUES (15, 'disconnect test')",
            (),
            options=ExecutionOptions(stmt_type=StatementType.INSERT),
        )

        await backend.disconnect()

        assert backend._transaction_manager is None
        assert backend._connection is None
        assert backend.in_transaction is False

        await backend.connect()
        row = await backend.fetch_one("SELECT * FROM test WHERE id = 15")
        assert row is None

    @pytest.mark.asyncio
    async def test_delete_on_close(self, temp_db_path):
        """Test deleting database file on close"""
        config = SQLiteConnectionConfig(database=temp_db_path, delete_on_close=True)
        backend = AsyncSQLiteBackend(connection_config=config)

        await backend.connect()
        await backend.execute(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)",
            (),
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        await backend.execute(
            "INSERT INTO test (id, value) VALUES (1, 'temp data')",
            (),
            options=ExecutionOptions(stmt_type=StatementType.INSERT),
        )

        assert os.path.exists(temp_db_path)

        await backend.disconnect()

        assert not os.path.exists(temp_db_path)
        assert not os.path.exists(temp_db_path + "-wal")
        assert not os.path.exists(temp_db_path + "-shm")
