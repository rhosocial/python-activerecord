# tests/rhosocial/activerecord_test/feature/backend/backend/test_backend_features_async.py
"""Async twin of test_backend_features.py: cursor/result-set/execute_many coverage on AsyncSQLiteBackend."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


class TestAsyncSQLiteBackendCoveragePart2:
    """Async twin of TestSQLiteBackendCoveragePart2"""

    def test_get_statement_type_default_branch(self):
        """Test _get_statement_type() default branch (calls super)"""
        # This method doesn't exist in current implementation, skipping test
        pass

    @pytest.mark.asyncio
    async def test_get_cursor_with_existing_cursor(self):
        """Test _get_cursor() lifecycle across disconnect/reconnect"""
        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()

        await backend.disconnect()
        assert backend._cursor is None

        await backend.connect()
        new_cursor = await backend._get_cursor()
        assert new_cursor is not None

        await backend.disconnect()

    @pytest_asyncio.fixture
    async def type_conversion_backend(self):
        """Backend with a test table holding convertible column values."""
        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()

        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute(
            """
            CREATE TABLE test (
                id INTEGER,
                name TEXT,
                created_at TEXT,
                is_active INTEGER,
                data TEXT,
                uuid_col TEXT
            )
        """,
            options=options,
        )

        test_uuid = uuid.uuid4()
        insert_options = ExecutionOptions(stmt_type=StatementType.INSERT)
        await backend.execute(
            f"""
            INSERT INTO test VALUES
            (1, 'test', '2024-01-01 10:00:00', 1, '{{"key": "value"}}', '{test_uuid}')
        """,
            options=insert_options,
        )

        yield backend, test_uuid
        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_process_result_set_with_type_conversion(self, type_conversion_backend):
        """Test result processing with column type conversion"""
        backend, test_uuid = type_conversion_backend

        datetime_adapter = backend.adapter_registry.get_adapter(datetime, str)
        bool_adapter = backend.adapter_registry.get_adapter(bool, int)
        json_adapter = backend.adapter_registry.get_adapter(dict, str)
        uuid_adapter = backend.adapter_registry.get_adapter(uuid.UUID, str)

        column_adapters_for_test = {
            "created_at": (datetime_adapter, datetime),
            "is_active": (bool_adapter, bool),
            "data": (json_adapter, dict),
            "uuid_col": (uuid_adapter, uuid.UUID),
        }

        result = await backend.fetch_one("SELECT * FROM test", column_adapters=column_adapters_for_test)
        assert result["id"] == 1
        assert result["name"] == "test"
        assert isinstance(result["created_at"], datetime)
        assert result["is_active"] is True
        assert isinstance(result["data"], dict)
        assert result["data"] == {"key": "value"}
        assert isinstance(result["uuid_col"], uuid.UUID)
        assert result["uuid_col"] == test_uuid

        class MockAdapter:
            def from_database(self, value, target_type=None):
                return f"adapted:{value}"

            @property
            def supported_types(self):
                return {}

        mock_adapter_instance = MockAdapter()
        column_adapters_mock = {"name": (mock_adapter_instance, str)}
        result = await backend.fetch_one("SELECT * FROM test", column_adapters=column_adapters_mock)
        assert result["name"] == "adapted:test"

        class InvalidAdapter:
            pass

        column_adapters_invalid = {"name": (InvalidAdapter(), str)}

        with pytest.raises(AttributeError):
            await backend.fetch_one("SELECT * FROM test", column_adapters=column_adapters_invalid)

    @pytest.mark.asyncio
    async def test_process_result_set_with_tuple_rows(self):
        """Test result processing with tuple-like rows"""
        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()

        mock_cursor = MagicMock()
        mock_cursor.fetchall = AsyncMock(return_value=[(1, "test", True)])
        mock_cursor.description = [("id",), ("name",), ("is_active",)]

        bool_adapter = backend.adapter_registry.get_adapter(bool, int)

        column_adapters_for_test = {"is_active": (bool_adapter, bool)}

        result = await backend._process_result_set(
            mock_cursor, is_select=True, column_adapters=column_adapters_for_test
        )

        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["name"] == "test"
        assert result[0]["is_active"] is True

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_execute_many(self):
        """Test execute_many() method"""
        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()

        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute("CREATE TABLE test (id INTEGER, name TEXT)", options=options)

        params_list = [(1, "test1"), (2, "test2"), (3, "test3")]

        result = await backend.execute_many("INSERT INTO test (id, name) VALUES (?, ?)", params_list)

        assert result.affected_rows == 3
        assert result.duration > 0

        rows = await backend.fetch_all("SELECT * FROM test ORDER BY id")
        assert len(rows) == 3
        assert rows[0]["name"] == "test1"
        assert rows[2]["name"] == "test3"

        result = await backend.execute_many("INSERT INTO test (id, name) VALUES (?, ?)", [])
        assert result.affected_rows == 0

        with pytest.raises(Exception):  # noqa: B017
            await backend.execute_many("INSERT INTO invalid_table VALUES (?, ?)", [(1, "test")])

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_execute_many_without_connection(self):
        """Test execute_many() without connection (auto-connect)"""
        backend = AsyncSQLiteBackend(database=":memory:")

        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER, name TEXT)", options=options)

        params_list = [(1, "test")]

        await backend.execute_many("INSERT INTO test VALUES (?, ?)", params_list)

        assert backend._connection is not None

        result = await backend.fetch_all("SELECT * FROM test")
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["name"] == "test"

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_handle_auto_commit_exception(self):
        """Test _handle_auto_commit() exception handling"""
        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()

        conn = backend._connection
        await conn.close()

        # Should not raise exception, just log warning
        await backend._handle_auto_commit()

        # Restore connection for cleanup
        backend._connection = None

    @pytest.mark.asyncio
    async def test_handle_auto_commit_without_connection(self):
        """Test _handle_auto_commit() without connection"""
        backend = AsyncSQLiteBackend(database=":memory:")

        # Should not raise exception
        await backend._handle_auto_commit()
