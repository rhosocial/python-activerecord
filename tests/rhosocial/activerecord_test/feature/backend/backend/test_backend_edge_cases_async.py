# tests/rhosocial/activerecord_test/feature/backend/backend/test_backend_edge_cases_async.py
"""Async twin of test_backend_edge_cases.py for AsyncSQLiteBackend edge cases."""

import os
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import aiofiles
import pytest

from rhosocial.activerecord.backend.errors import ConnectionError
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


class TestAsyncSQLiteBackendCoveragePart3Fixed:
    """Async twins of edge case tests for the SQLite backend - Part 3"""

    @pytest.mark.asyncio
    async def test_disconnect_delete_on_close_max_retries(self, tmp_path):
        """Test disconnect with delete_on_close when all retries fail"""
        db_path = str(tmp_path / "test.db")
        config = SQLiteConnectionConfig(database=db_path, delete_on_close=True)
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute("CREATE TABLE test (id INTEGER)", options=options)

        original_remove = aiofiles.os.remove
        remove_calls = []

        async def mock_remove(path):
            remove_calls.append(path)
            if path == db_path:
                raise OSError("Mocked permission error")
            return await original_remove(path)

        with patch("aiofiles.os.remove", mock_remove), patch("aiofiles.os.path.exists",
                                                             AsyncMock(return_value=True)):
            await backend.disconnect()

            assert remove_calls.count(db_path) == 5
            assert backend._connection is None

    @pytest.mark.asyncio
    async def test_disconnect_delete_on_close_file_not_exists(self, tmp_path):
        """Test disconnect with delete_on_close when files don't exist"""
        db_path = str(tmp_path / "nonexistent.db")
        config = SQLiteConnectionConfig(database=db_path, delete_on_close=True)
        backend = AsyncSQLiteBackend(connection_config=config)

        await backend.connect()

        with patch("aiofiles.os.path.exists", AsyncMock(return_value=False)):
            await backend.disconnect()

            assert backend._connection is None

    @pytest.mark.asyncio
    async def test_connect_with_uri_option(self):
        """Test connect with URI option"""
        config = SQLiteConnectionConfig(database=":memory:", uri=True)
        backend = AsyncSQLiteBackend(connection_config=config)

        await backend.connect()
        assert backend._connection is not None

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_pragma_settings_edge_cases(self):
        """Test edge cases in pragma settings"""
        config1 = SQLiteConnectionConfig(database=":memory:")
        backend1 = AsyncSQLiteBackend(connection_config=config1)
        pragmas1 = backend1.pragmas
        assert all(key in pragmas1 for key in SQLiteConnectionConfig.DEFAULT_PRAGMAS)

        config2 = SQLiteConnectionConfig(database=":memory:", pragmas={})
        backend2 = AsyncSQLiteBackend(connection_config=config2)
        pragmas2 = backend2.pragmas
        assert all(key in pragmas2 for key in SQLiteConnectionConfig.DEFAULT_PRAGMAS)

        config3 = SQLiteConnectionConfig(database=":memory:", pragmas={"numeric_pragma": 123, "boolean_pragma": True})
        backend3 = AsyncSQLiteBackend(connection_config=config3)
        pragmas3 = backend3.pragmas
        assert "numeric_pragma" in pragmas3
        assert "boolean_pragma" in pragmas3

    @pytest.mark.asyncio
    async def test_set_pragma_without_connection(self):
        """Test set_pragma when not connected"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)

        await backend.set_pragma("journal_mode", "WAL")
        assert backend.pragmas["journal_mode"] == "WAL"

        # Unknown pragma name is rejected by the whitelist validation
        with pytest.raises(ValueError):
            await backend.set_pragma("test_pragma", "test_value")

        await backend.connect()

        # Verify the pragma query executes without error on the live connection
        row = await backend.fetch_one("PRAGMA journal_mode")
        assert row is not None

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_prepare_parameters_with_uuid(self):
        """Test that prepare_parameters properly handles UUID objects"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)

        uuid_adapter = backend.adapter_registry.get_adapter(uuid.UUID, str)

        test_uuid = uuid.uuid4()

        params_dict = {"id": test_uuid, "name": "test_name", "value": 123}

        param_adapters_dict = {
            "id": (uuid_adapter, str),
            "name": None,
            "value": None,
        }

        prepared_params = backend.prepare_parameters(params_dict, param_adapters_dict)

        assert isinstance(prepared_params["id"], str)
        assert prepared_params["id"] == str(test_uuid)
        assert prepared_params["name"] == "test_name"
        assert prepared_params["value"] == 123

        params_seq = (test_uuid, "test_name", 123)
        param_adapters_seq = [
            (uuid_adapter, str),
            None,
            None,
        ]

        prepared_seq = backend.prepare_parameters(params_seq, param_adapters_seq)

        assert isinstance(prepared_seq[0], str)
        assert prepared_seq[0] == str(test_uuid)
        assert prepared_seq[1] == "test_name"
        assert prepared_seq[2] == 123

    @pytest.mark.asyncio
    async def test_prepare_parameters_with_multiple_types(self):
        """Test that prepare_parameters properly handles multiple types"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)

        uuid_adapter = backend.adapter_registry.get_adapter(uuid.UUID, str)
        datetime_adapter = backend.adapter_registry.get_adapter(datetime, str)
        json_adapter = backend.adapter_registry.get_adapter(dict, str)

        test_uuid = uuid.uuid4()
        test_datetime = datetime(2024, 1, 1, 12, 0, 0)
        test_dict = {"key": "value", "nested": {"inner": "value"}}

        params_dict = {
            "uuid_col": test_uuid,
            "datetime_col": test_datetime,
            "json_col": test_dict,
            "regular_col": "normal_string",
        }

        param_adapters_dict = {
            "uuid_col": (uuid_adapter, str),
            "datetime_col": (datetime_adapter, str),
            "json_col": (json_adapter, str),
            "regular_col": None,
        }

        prepared_params = backend.prepare_parameters(params_dict, param_adapters_dict)

        assert isinstance(prepared_params["uuid_col"], str)
        assert prepared_params["uuid_col"] == str(test_uuid)

        assert isinstance(prepared_params["datetime_col"], str)
        assert prepared_params["datetime_col"] == test_datetime.isoformat()

        assert isinstance(prepared_params["json_col"], str)
        import json

        parsed_json = json.loads(prepared_params["json_col"])
        assert parsed_json == test_dict

        assert prepared_params["regular_col"] == "normal_string"

    @pytest.mark.asyncio
    async def test_execute_with_prepared_uuid_parameters(self):
        """Test that prepared UUID parameters work correctly in actual database operations"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute(
            """
            CREATE TABLE test_uuid (
                id TEXT PRIMARY KEY,
                name TEXT
            )
        """,
            options=options,
        )

        uuid_adapter = backend.adapter_registry.get_adapter(uuid.UUID, str)

        test_uuid = uuid.uuid4()

        params = (test_uuid, "test_name")
        param_adapters = [
            (uuid_adapter, str),
            None,
        ]

        prepared_params = backend.prepare_parameters(params, param_adapters)

        insert_options = ExecutionOptions(stmt_type=StatementType.INSERT)
        result = await backend.execute(
            "INSERT INTO test_uuid (id, name) VALUES (?, ?)", prepared_params, options=insert_options
        )

        assert result.affected_rows == 1

        rows = await backend.fetch_all("SELECT * FROM test_uuid WHERE name = ?", ("test_name",))
        assert len(rows) == 1
        assert rows[0]["id"] == str(test_uuid)
        assert rows[0]["name"] == "test_name"

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_execute_many_parameter_adaption(self):
        """Test that execute_many properly handles pre-adapted parameters"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute(
            """
            CREATE TABLE test (
                id INTEGER,
                data TEXT,
                created_at TEXT
            )
        """,
            options=options,
        )

        datetime_adapter = backend.adapter_registry.get_adapter(datetime, str)
        json_adapter = backend.adapter_registry.get_adapter(dict, str)

        raw_params_list = [(1, {"key": "value1"}, datetime(2024, 1, 1)), (2, {"key": "value2"}, datetime(2024, 1, 2))]

        param_adapters_spec = [
            None,
            (json_adapter, str),
            (datetime_adapter, str),
        ]

        processed_params_list = []
        for params in raw_params_list:
            processed_params_list.append(backend.prepare_parameters(params, param_adapters_spec))

        result = await backend.execute_many(
            "INSERT INTO test (id, data, created_at) VALUES (?, ?, ?)",
            processed_params_list,
        )

        assert result.affected_rows == 2

        rows = await backend.fetch_all("SELECT * FROM test ORDER BY id")
        assert len(rows) == 2
        assert isinstance(rows[0]["data"], str)
        assert isinstance(rows[0]["created_at"], str)

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_execute_many_empty_params(self):
        """Test execute_many with empty parameter lists"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute("CREATE TABLE test (id INTEGER)", options=options)

        result = await backend.execute_many("INSERT INTO test (id) VALUES (?)", [])
        assert result.affected_rows == 0

        result = await backend.execute_many("INSERT INTO test DEFAULT VALUES", [(), (), ()])
        assert result.affected_rows == 3

        result = await backend.execute_many("INSERT INTO test(id) VALUES (?)", [(1,), (2,), (3,)])
        assert result.affected_rows == 3

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_cursor_management_edge_cases(self):
        """Test edge cases in cursor management"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        await backend.disconnect()
        assert backend._cursor is None

        await backend.connect()
        new_cursor = await backend._get_cursor()
        assert new_cursor is not None

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_transaction_during_disconnect(self):
        """Test behavior when disconnecting with active transaction"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute("CREATE TABLE test (id INTEGER, value TEXT)", options=options)

        await backend.begin_transaction()

        insert_options = ExecutionOptions(stmt_type=StatementType.INSERT)
        await backend.execute("INSERT INTO test VALUES (1, 'test')", options=insert_options)

        await backend.disconnect()

        await backend.connect()
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute("CREATE TABLE test (id INTEGER, value TEXT)", options=options)
        result = await backend.fetch_all("SELECT * FROM test")
        assert len(result) == 0

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_auto_commit_with_error_in_commit(self):
        """Test auto commit when commit raises an error"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        mock_tm = MagicMock()
        mock_tm.is_active = False
        backend._transaction_manager = mock_tm

        await backend._connection.close()

        await backend._handle_auto_commit()

        backend._connection = None

    @pytest.mark.asyncio
    async def test_disconnect_delete_files_exception_fixed(self, tmp_path):
        """Test disconnect() raises ConnectionError on file deletion failure"""
        db_path = str(tmp_path / "test.db")
        config = SQLiteConnectionConfig(database=db_path, delete_on_close=True)
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute("CREATE TABLE test (id INTEGER)", options=options)

        # Deletion failure must propagate as ConnectionError, mirroring the sync backend
        with patch("aiofiles.os.remove", AsyncMock(side_effect=Exception("Unexpected error"))), patch(
            "aiofiles.os.path.exists", AsyncMock(return_value=True)
        ):
            with pytest.raises(ConnectionError, match="Failed to delete database files"):
                await backend.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_transaction_manager_cleanup(self):
        """Test that disconnect cleans up transaction manager"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        _ = backend.transaction_manager
        assert backend._transaction_manager is not None

        await backend.disconnect()
        assert backend._transaction_manager is None

    @pytest.mark.asyncio
    async def test_uuid_type_adaptation_full_flow(self):
        """Test full flow of UUID type adaptation from save to query operations"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute(
            """
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                name TEXT,
                external_id TEXT
            )
        """,
            options=options,
        )

        user_id = uuid.uuid4()
        external_id = uuid.uuid4()

        insert_options = ExecutionOptions(stmt_type=StatementType.INSERT)
        result = await backend.execute(
            "INSERT INTO users (id, name, external_id) VALUES (?, ?, ?)",
            (user_id, "John Doe", external_id),
            options=insert_options,
        )
        assert result.affected_rows == 1

        user_fetched = await backend.fetch_one(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        )
        assert user_fetched is not None
        assert user_fetched["id"] == str(user_id)
        assert user_fetched["name"] == "John Doe"
        assert user_fetched["external_id"] == str(external_id)

        user_by_external = await backend.fetch_one(
            "SELECT * FROM users WHERE external_id = ?",
            (external_id,),
        )
        assert user_by_external is not None
        assert user_by_external["id"] == str(user_id)
        assert user_by_external["external_id"] == str(external_id)

        users = await backend.fetch_all(
            "SELECT * FROM users WHERE id = ? OR external_id = ?",
            (user_id, external_id),
        )
        assert len(users) == 1
        assert users[0]["id"] == str(user_id)
        assert users[0]["external_id"] == str(external_id)

        another_user_id = uuid.uuid4()
        another_ext_id = uuid.uuid4()

        await backend.execute(
            "INSERT INTO users (id, name, external_id) VALUES (?, ?, ?)",
            (another_user_id, "Jane Smith", another_ext_id),
            options=insert_options,
        )

        multiple_users = await backend.fetch_all(
            "SELECT * FROM users WHERE id = ? OR external_id = ?",
            (user_id, another_ext_id),
        )
        assert len(multiple_users) == 2
        found_ids = {user["id"] for user in multiple_users}
        assert str(user_id) in found_ids
        assert str(another_user_id) in found_ids

        await backend.fetch_one("SELECT typeof(id) as id_type, typeof(external_id) as ext_type FROM users LIMIT 1")
        sample_user = await backend.fetch_one("SELECT id, external_id FROM users LIMIT 1")
        assert isinstance(sample_user["id"], str)
        assert isinstance(sample_user["external_id"], str)
        parsed_id = uuid.UUID(sample_user["id"])
        parsed_ext = uuid.UUID(sample_user["external_id"])
        assert isinstance(parsed_id, uuid.UUID)
        assert isinstance(parsed_ext, uuid.UUID)

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_uuid_type_adaptation_with_column_adapters(self):
        """Test UUID type adaptation with column adapters for result processing"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute(
            """
            CREATE TABLE products (
                id TEXT PRIMARY KEY,
                name TEXT,
                category_id TEXT
            )
        """,
            options=options,
        )

        uuid_adapter = backend.adapter_registry.get_adapter(uuid.UUID, str)

        product_id = uuid.uuid4()
        category_id = uuid.uuid4()

        insert_options = ExecutionOptions(stmt_type=StatementType.INSERT)
        result = await backend.execute(
            "INSERT INTO products (id, name, category_id) VALUES (?, ?, ?)",
            (product_id, "Test Product", category_id),
            options=insert_options,
        )
        assert result.affected_rows == 1

        column_adapters = {
            "id": (uuid_adapter, uuid.UUID),
            "category_id": (uuid_adapter, uuid.UUID),
        }

        product = await backend.fetch_one(
            "SELECT * FROM products WHERE id = ?",
            (product_id,),
            column_adapters=column_adapters,
        )

        assert product is not None
        assert isinstance(product["id"], uuid.UUID)
        assert product["id"] == product_id
        assert product["name"] == "Test Product"
        assert isinstance(product["category_id"], uuid.UUID)
        assert product["category_id"] == category_id

        products = await backend.fetch_all(
            "SELECT * FROM products WHERE category_id = ?",
            (category_id,),
            column_adapters=column_adapters,
        )

        assert len(products) == 1
        product2 = products[0]
        assert isinstance(product2["id"], uuid.UUID)
        assert product2["id"] == product_id
        assert isinstance(product2["category_id"], uuid.UUID)
        assert product2["category_id"] == category_id

        await backend.disconnect()
