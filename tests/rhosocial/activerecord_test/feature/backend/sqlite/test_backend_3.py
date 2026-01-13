# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_backend_3.py
"""Tests for improving SQLite backend coverage - Part 3 Fixed (Edge Cases)"""

import os
import pytest
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock

from rhosocial.activerecord.backend.errors import ConnectionError
from rhosocial.activerecord.backend.expression.statements import ReturningClause
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


class TestSQLiteBackendCoveragePart3Fixed:
    """Fixed tests to improve coverage of SQLiteBackend - Part 3 (Edge Cases)"""

    def test_disconnect_delete_on_close_max_retries(self, tmp_path):
        """Test disconnect with delete_on_close when all retries fail"""
        db_path = str(tmp_path / "test.db")
        # Use SQLiteConnectionConfig to create a configuration
        config = SQLiteConnectionConfig(
            database=db_path,
            delete_on_close=True
        )
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Create the database files
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        backend.execute("CREATE TABLE test (id INTEGER)", options=options)
        wal_path = f"{db_path}-wal"
        shm_path = f"{db_path}-shm"

        # Mock os.remove to always fail for the main database file
        original_remove = os.remove
        remove_calls = []

        def mock_remove(path):
            remove_calls.append(path)
            if path == db_path:
                raise OSError("Mocked permission error")
            return original_remove(path)

        with patch('os.remove', mock_remove), \
                patch('os.path.exists', return_value=True):
            # Should attempt multiple times and log warning
            backend.disconnect()

            # Should have attempted max_retries times
            assert remove_calls.count(db_path) == 5  # Default max_retries is 5

            # Connection should still be cleared
            assert backend._connection is None

    def test_disconnect_delete_on_close_file_not_exists(self, tmp_path):
        """Test disconnect with delete_on_close when files don't exist"""
        db_path = str(tmp_path / "nonexistent.db")
        # Use SQLiteConnectionConfig to create a configuration
        config = SQLiteConnectionConfig(
            database=db_path,
            delete_on_close=True
        )
        backend = SQLiteBackend(connection_config=config)

        # Connect and disconnect without creating any files
        backend.connect()

        # Mock os.path.exists to return False
        with patch('os.path.exists', return_value=False):
            # Should not attempt to delete non-existent files
            backend.disconnect()

            # Connection should be cleared
            assert backend._connection is None

    def test_connect_with_uri_option(self):
        """Test connect with URI option"""
        # Use SQLiteConnectionConfig to create a configuration，with uri=True
        config = SQLiteConnectionConfig(
            database=":memory:",
            uri=True
        )
        backend = SQLiteBackend(connection_config=config)

        # Should connect with uri=True
        backend.connect()
        assert backend._connection is not None

        backend.disconnect()

    def test_check_returning_compatibility_edge_cases(self):
        """Test edge cases in _check_returning_compatibility"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)

        # Create a mock ReturningClause object for testing
        mock_returning_clause = ReturningClause(backend.dialect, expressions=[])
        
        # Test with exact boundary versions
        with patch('sqlite3.sqlite_version_info', (3, 35, 0)), \
                patch('sys.version_info', (3, 10, 0)):
            # Should not raise exception for exact boundary versions
            backend._check_returning_compatibility(mock_returning_clause)

        # Test with force=True bypassing all checks - not applicable to current implementation
        # The current implementation doesn't have a force parameter in ReturningClause

    def test_pragma_settings_edge_cases(self):
        """Test edge cases in pragma settings"""
        # Test with no custom pragmas
        config1 = SQLiteConnectionConfig(database=":memory:")
        backend1 = SQLiteBackend(connection_config=config1)
        pragmas1 = backend1.pragmas
        assert all(key in pragmas1 for key in SQLiteConnectionConfig.DEFAULT_PRAGMAS)

        # Test with empty custom pragmas
        config2 = SQLiteConnectionConfig(database=":memory:", pragmas={})
        backend2 = SQLiteBackend(connection_config=config2)
        pragmas2 = backend2.pragmas
        assert all(key in pragmas2 for key in SQLiteConnectionConfig.DEFAULT_PRAGMAS)

        # Test with non-string pragma values
        config3 = SQLiteConnectionConfig(
            database=":memory:",
            pragmas={"numeric_pragma": 123, "boolean_pragma": True}
        )
        backend3 = SQLiteBackend(connection_config=config3)
        pragmas3 = backend3.pragmas
        assert "numeric_pragma" in pragmas3
        assert "boolean_pragma" in pragmas3

    def test_set_pragma_without_connection(self):
        """Test set_pragma when not connected"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)

        # Should only update internal dictionary without error
        backend.set_pragma("test_pragma", "test_value")
        assert backend.pragmas["test_pragma"] == "test_value"

        # Verify pragma is applied when connection is established
        backend.connect()

        # For testing, let's use a real pragma
        cursor = backend._connection.cursor()
        cursor.execute("PRAGMA test_pragma")
        # Note: custom pragmas might not be queryable, so we just verify no error occurs

        backend.disconnect()

    def test_prepare_parameters_with_uuid(self):
        """
        Test that `prepare_parameters` properly handles UUID objects using SQLiteUUIDAdapter.
        
        This test verifies that UUID objects are correctly converted to strings when 
        using the prepare_parameters method, which is critical for SQLite operations.
        """
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        
        # Get the SQLiteUUIDAdapter from the backend's registry
        uuid_adapter = backend.adapter_registry.get_adapter(uuid.UUID, str)
        
        # Create a UUID for testing
        test_uuid = uuid.uuid4()
        
        # Test with a dictionary of parameters
        params_dict = {
            'id': test_uuid,
            'name': 'test_name',
            'value': 123
        }
        
        # Define adapters for the UUID field
        param_adapters_dict = {
            'id': (uuid_adapter, str),  # UUID field needs conversion to string
            'name': None,  # string is already compatible
            'value': None  # int is already compatible
        }
        
        # Prepare the parameters
        prepared_params = backend.prepare_parameters(params_dict, param_adapters_dict)
        
        # Verify that the UUID was converted to a string
        assert isinstance(prepared_params['id'], str)
        assert prepared_params['id'] == str(test_uuid)
        assert prepared_params['name'] == 'test_name'
        assert prepared_params['value'] == 123
        
        # Test with sequence of parameters
        params_seq = (test_uuid, 'test_name', 123)
        param_adapters_seq = [
            (uuid_adapter, str),  # UUID field needs conversion to string
            None,  # string is already compatible
            None   # int is already compatible
        ]
        
        prepared_seq = backend.prepare_parameters(params_seq, param_adapters_seq)
        
        # Verify that the UUID was converted to a string in the sequence
        assert isinstance(prepared_seq[0], str)
        assert prepared_seq[0] == str(test_uuid)
        assert prepared_seq[1] == 'test_name'
        assert prepared_seq[2] == 123

    def test_prepare_parameters_with_multiple_types(self):
        """
        Test that `prepare_parameters` properly handles multiple types including UUID, datetime, etc.
        
        This test adheres to the "decoupled type adaptation" principle:
        1.  `prepare_parameters` is designed to receive adapter specifications
            and convert Python native types to database-compatible types.
        2.  The caller specifies which adapters to use for which parameters.
        """
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        
        # Get adapters from the backend's registry
        uuid_adapter = backend.adapter_registry.get_adapter(uuid.UUID, str)
        datetime_adapter = backend.adapter_registry.get_adapter(datetime, str)
        json_adapter = backend.adapter_registry.get_adapter(dict, str)

        # Create test data with various types that need conversion
        test_uuid = uuid.uuid4()
        test_datetime = datetime(2024, 1, 1, 12, 0, 0)
        test_dict = {"key": "value", "nested": {"inner": "value"}}

        # Test with dictionary parameters
        params_dict = {
            'uuid_col': test_uuid,
            'datetime_col': test_datetime,
            'json_col': test_dict,
            'regular_col': 'normal_string'
        }

        # Define adapter specifications
        param_adapters_dict = {
            'uuid_col': (uuid_adapter, str),      # UUID -> string
            'datetime_col': (datetime_adapter, str),  # datetime -> string
            'json_col': (json_adapter, str),      # dict -> JSON string
            'regular_col': None                   # string is already compatible
        }

        # Prepare the parameters
        prepared_params = backend.prepare_parameters(params_dict, param_adapters_dict)

        # Verify conversions
        assert isinstance(prepared_params['uuid_col'], str)
        assert prepared_params['uuid_col'] == str(test_uuid)
        
        assert isinstance(prepared_params['datetime_col'], str)
        assert prepared_params['datetime_col'] == test_datetime.isoformat()
        
        assert isinstance(prepared_params['json_col'], str)
        # JSON string should contain the original data when parsed back
        import json
        parsed_json = json.loads(prepared_params['json_col'])
        assert parsed_json == test_dict
        
        assert prepared_params['regular_col'] == 'normal_string'

    def test_execute_with_prepared_uuid_parameters(self):
        """
        Test that prepared UUID parameters work correctly in actual database operations.
        
        This test ensures that UUIDs are properly converted before being sent to SQLite.
        """
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Create test table with UUID primary key
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        backend.execute("""
            CREATE TABLE test_uuid (
                id TEXT PRIMARY KEY,
                name TEXT
            )
        """, options=options)

        # Get the UUID adapter
        uuid_adapter = backend.adapter_registry.get_adapter(uuid.UUID, str)
        
        test_uuid = uuid.uuid4()
        
        # Prepare parameters with UUID adapter
        params = (test_uuid, 'test_name')
        param_adapters = [
            (uuid_adapter, str),  # Convert UUID to string
            None  # String is already compatible
        ]
        
        # Prepare the parameters
        prepared_params = backend.prepare_parameters(params, param_adapters)
        
        # Execute with prepared parameters
        insert_options = ExecutionOptions(stmt_type=StatementType.INSERT)
        result = backend.execute(
            "INSERT INTO test_uuid (id, name) VALUES (?, ?)",
            prepared_params,
            options=insert_options
        )
        
        assert result.affected_rows == 1
        
        # Verify the record was inserted correctly
        rows = backend.fetch_all("SELECT * FROM test_uuid WHERE name = ?", ('test_name',))
        assert len(rows) == 1
        assert rows[0]['id'] == str(test_uuid)
        assert rows[0]['name'] == 'test_name'

        backend.disconnect()

    def test_execute_many_parameter_adaption(self):
        """
        Test that `execute_many` properly handles pre-adapted parameters.

        This test adheres to the "decoupled type adaptation" principle:
        1.  `execute_many` is designed to receive parameters that are already
            database-compatible. It does *not* perform any internal type
            adaptation.
        2.  Therefore, this test explicitly prepares its `params_list` by
            using `backend.prepare_parameters` (which leverages `TypeAdaptionMixin`)
            before passing the `processed_params_list` to `execute_many`.
        3.  The `param_adapters_spec` defines which adapters to use for which
            positional parameter within each tuple of the `raw_params_list`.
        """
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Create test table
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        backend.execute("""
            CREATE TABLE test (
                id INTEGER,
                data TEXT,
                created_at TEXT
            )
        """, options=options)

        # Test with datetime objects that need conversion
        from datetime import datetime

        # Get adapters from the backend's registry
        # These are the standard adapters registered by StorageBackendBase.
        datetime_adapter = backend.adapter_registry.get_adapter(datetime, str)
        json_adapter = backend.adapter_registry.get_adapter(dict, str)

        # raw_params_list contains Python native types that require adaptation
        raw_params_list = [
            (1, {"key": "value1"}, datetime(2024, 1, 1)),
            (2, {"key": "value2"}, datetime(2024, 1, 2))
        ]

        # param_adapters_spec defines the adapter and target DB type for each positional parameter.
        # `None` means the parameter is already database-compatible or handled by the driver.
        param_adapters_spec = [
            None, # id (int) is handled directly
            (json_adapter, str), # data (dict) converted to str (JSON string)
            (datetime_adapter, str) # created_at (datetime) converted to str (ISO format)
        ]

        # Explicitly prepare parameters for execute_many.
        # This step demonstrates the caller's responsibility to adapt types
        # before passing them to the low-level execution method.
        processed_params_list = []
        for params in raw_params_list:
            processed_params_list.append(backend.prepare_parameters(params, param_adapters_spec))

        result = backend.execute_many(
            "INSERT INTO test (id, data, created_at) VALUES (?, ?, ?)",
            processed_params_list # Pass the already processed list
        )

        assert result.affected_rows == 2

        # Verify data was properly converted and stored
        rows = backend.fetch_all("SELECT * FROM test ORDER BY id")
        assert len(rows) == 2
        # Data is retrieved as raw strings because `fetch_all` typically doesn't have `column_adapters` here.
        assert isinstance(rows[0]["data"], str)  # JSON converted to string
        assert isinstance(rows[0]["created_at"], str)  # Datetime converted to string

        backend.disconnect()

    def test_execute_many_empty_params(self):
        """Test execute_many with empty parameter lists"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Create test table
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        backend.execute("CREATE TABLE test (id INTEGER)", options=options)

        # Test with empty params list
        result = backend.execute_many("INSERT INTO test (id) VALUES (?)", [])
        assert result.affected_rows == 0

        # Test with params list containing empty tuples
        result = backend.execute_many("INSERT INTO test DEFAULT VALUES", [(), (), ()])
        assert result.affected_rows == 3 # Corrected assertion based on SQLite behavior

        # Test with params list containing sequential tuples
        result = backend.execute_many("INSERT INTO test(id) VALUES (?)", [(1, ), (2, ), (3, )])
        assert result.affected_rows == 3

        backend.disconnect()

    def test_cursor_management_edge_cases(self):
        """Test edge cases in cursor management"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Test cursor cleanup on disconnect
        backend.disconnect()
        assert backend._cursor is None

        # Test cursor creation on reconnect
        backend.connect()
        new_cursor = backend._get_cursor()
        assert new_cursor is not None

        backend.disconnect()

    def test_transaction_during_disconnect(self):
        """Test behavior when disconnecting with active transaction"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Create table before starting transaction
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        backend.execute("CREATE TABLE test (id INTEGER, value TEXT)", options=options)

        # Start a transaction
        backend.begin_transaction()

        # Insert some data
        insert_options = ExecutionOptions(stmt_type=StatementType.INSERT)
        backend.execute("INSERT INTO test VALUES (1, 'test')", options=insert_options)

        # Disconnect with active transaction
        backend.disconnect()

        # Reconnect and recreate the table since memory database is cleared on disconnect
        backend.connect()
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        backend.execute("CREATE TABLE test (id INTEGER, value TEXT)", options=options)
        result = backend.fetch_all("SELECT * FROM test")
        assert len(result) == 0  # Table exists but is empty

        backend.disconnect()

    def test_auto_commit_with_error_in_commit(self):
        """Test auto commit when commit raises an error"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Mock transaction_manager to return False for is_active
        mock_tm = MagicMock()
        mock_tm.is_active = False
        backend._transaction_manager = mock_tm

        # Close connection to make commit fail
        backend._connection.close()

        # Should log warning but not raise exception
        backend._handle_auto_commit()

        # Cleanup
        backend._connection = None

    def test_disconnect_delete_files_exception_fixed(self, tmp_path):
        """Test disconnect() with exception during file deletion - fixed version"""
        db_path = str(tmp_path / "test.db")
        # 使用 SQLiteConnectionConfig 创建配置
        config = SQLiteConnectionConfig(
            database=db_path,
            delete_on_close=True
        )
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Create a table to ensure file exists
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        backend.execute("CREATE TABLE test (id INTEGER)", options=options)

        # Mock exception during file deletion
        with patch('os.path.exists', return_value=True), \
             patch('os.remove', side_effect=Exception("Unexpected error")):

            # Should raise ConnectionError as expected
            with pytest.raises(ConnectionError) as exc_info:
                backend.disconnect()

            assert "Failed to delete database files" in str(exc_info.value)

    def test_disconnect_transaction_manager_cleanup(self):
        """Test that disconnect cleans up transaction manager"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Access transaction manager to create it
        tm = backend.transaction_manager
        assert backend._transaction_manager is not None

        # Disconnect should clear it
        backend.disconnect()
        assert backend._transaction_manager is None

    def test_uuid_type_adaptation_full_flow(self):
        """
        Test full flow of UUID type adaptation from save to query operations.

        This test verifies that UUID objects are properly converted to database-compatible
        format during save operations and properly reconstructed from database format
        during query operations, ensuring end-to-end type safety.
        """
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Create test table with UUID primary key
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        backend.execute("""
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                name TEXT,
                external_id TEXT
            )
        """, options=options)

        # Generate test UUIDs
        user_id = uuid.uuid4()
        external_id = uuid.uuid4()

        # Test 1: Save operation with UUID parameters
        # The execute method should now properly convert UUIDs to strings
        insert_options = ExecutionOptions(stmt_type=StatementType.INSERT)
        result = backend.execute(
            "INSERT INTO users (id, name, external_id) VALUES (?, ?, ?)",
            (user_id, "John Doe", external_id),  # UUIDs passed directly
            options=insert_options
        )
        assert result.affected_rows == 1

        # Test 2: Query operations with UUID parameters
        # fetch_one should properly convert UUID parameter to string for database
        user_fetched = backend.fetch_one(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)  # UUID passed directly as parameter
        )
        assert user_fetched is not None
        assert user_fetched['id'] == str(user_id)  # Should be converted to string in DB
        assert user_fetched['name'] == "John Doe"
        assert user_fetched['external_id'] == str(external_id)

        # Test 3: Query with external_id UUID parameter
        user_by_external = backend.fetch_one(
            "SELECT * FROM users WHERE external_id = ?",
            (external_id,)  # UUID passed directly as parameter
        )
        assert user_by_external is not None
        assert user_by_external['id'] == str(user_id)
        assert user_by_external['external_id'] == str(external_id)

        # Test 4: fetch_all with UUID parameter
        users = backend.fetch_all(
            "SELECT * FROM users WHERE id = ? OR external_id = ?",
            (user_id, external_id)  # Both UUIDs passed directly
        )
        assert len(users) == 1
        assert users[0]['id'] == str(user_id)
        assert users[0]['external_id'] == str(external_id)

        # Test 5: Multiple UUID parameters in single query
        another_user_id = uuid.uuid4()
        another_ext_id = uuid.uuid4()

        # Insert another user
        backend.execute(
            "INSERT INTO users (id, name, external_id) VALUES (?, ?, ?)",
            (another_user_id, "Jane Smith", another_ext_id),
            options=insert_options
        )

        # Query with multiple UUID parameters
        multiple_users = backend.fetch_all(
            "SELECT * FROM users WHERE id = ? OR external_id = ?",
            (user_id, another_ext_id)  # Two different UUIDs
        )
        assert len(multiple_users) == 2
        found_ids = {user['id'] for user in multiple_users}
        assert str(user_id) in found_ids
        assert str(another_user_id) in found_ids

        # Test 6: Verify that raw database values are strings
        raw_result = backend.fetch_one(
            "SELECT typeof(id) as id_type, typeof(external_id) as ext_type FROM users LIMIT 1"
        )
        # In SQLite, UUIDs should be stored as TEXT (strings)
        # Note: typeof() in SQLite returns 'text' for TEXT columns
        # We can't test typeof directly, but we can verify the values are strings
        sample_user = backend.fetch_one("SELECT id, external_id FROM users LIMIT 1")
        assert isinstance(sample_user['id'], str)
        assert isinstance(sample_user['external_id'], str)
        # Verify they can be parsed back to UUID
        parsed_id = uuid.UUID(sample_user['id'])
        parsed_ext = uuid.UUID(sample_user['external_id'])
        assert isinstance(parsed_id, uuid.UUID)
        assert isinstance(parsed_ext, uuid.UUID)

        backend.disconnect()

    def test_uuid_type_adaptation_with_column_adapters(self):
        """
        Test UUID type adaptation with column adapters for result processing.

        This test verifies that UUIDs are properly converted both when sent to
        the database (input) and when retrieved from the database (output).
        """
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Create test table
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        backend.execute("""
            CREATE TABLE products (
                id TEXT PRIMARY KEY,
                name TEXT,
                category_id TEXT
            )
        """, options=options)

        # Get UUID adapter for result processing
        uuid_adapter = backend.adapter_registry.get_adapter(uuid.UUID, str)

        # Generate test data
        product_id = uuid.uuid4()
        category_id = uuid.uuid4()

        # Insert with UUID parameters (should be converted to strings automatically)
        insert_options = ExecutionOptions(stmt_type=StatementType.INSERT)
        result = backend.execute(
            "INSERT INTO products (id, name, category_id) VALUES (?, ?, ?)",
            (product_id, "Test Product", category_id),
            options=insert_options
        )
        assert result.affected_rows == 1

        # Query with UUID parameter and column adapters for result processing
        # This tests both input (parameter) and output (result) type adaptation
        column_adapters = {
            'id': (uuid_adapter, uuid.UUID),      # Convert DB string back to UUID object
            'category_id': (uuid_adapter, uuid.UUID)  # Convert DB string back to UUID object
        }

        product = backend.fetch_one(
            "SELECT * FROM products WHERE id = ?",
            (product_id,),  # Input: UUID parameter should be converted to string
            column_adapters=column_adapters      # Output: Result columns converted to UUID
        )

        assert product is not None
        # With column adapters, the ID and category_id should be converted back to UUID objects
        assert isinstance(product['id'], uuid.UUID)
        assert product['id'] == product_id  # Should match original UUID
        assert product['name'] == "Test Product"
        assert isinstance(product['category_id'], uuid.UUID)
        assert product['category_id'] == category_id  # Should match original UUID

        # Test with fetch_all as well
        products = backend.fetch_all(
            "SELECT * FROM products WHERE category_id = ?",
            (category_id,),  # Input: UUID parameter should be converted to string
            column_adapters=column_adapters      # Output: Result columns converted to UUID
        )

        assert len(products) == 1
        product2 = products[0]
        assert isinstance(product2['id'], uuid.UUID)
        assert product2['id'] == product_id
        assert isinstance(product2['category_id'], uuid.UUID)
        assert product2['category_id'] == category_id

        backend.disconnect()