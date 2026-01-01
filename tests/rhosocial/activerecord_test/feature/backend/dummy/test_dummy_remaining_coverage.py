"""
Final test suite to cover remaining uncovered lines in DummyBackend and DummyDialect.
"""
import pytest
from rhosocial.activerecord.backend.impl.dummy.backend import DummyBackend, AsyncDummyBackend
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.errors import DatabaseError


class TestDummyBackendRemainingCoverage:
    """Tests for remaining uncovered lines in DummyBackend."""
    
    def test_dummy_backend_all_methods(self):
        """Test all methods to ensure coverage."""
        backend = DummyBackend()
        
        # Test _initialize_capabilities (covers line 46)
        capabilities = backend._initialize_capabilities()
        assert capabilities is not None
        
        # Test get_server_version (covers line 79)
        version = backend.get_server_version()
        assert version == (0, 0, 0)
        
        # Test dialect property
        dialect = backend.dialect
        assert dialect is not None
        
        # Test connect method raises NotImplementedError
        with pytest.raises(NotImplementedError):
            backend.connect()
        
        # Test disconnect method (should not raise)
        backend.disconnect()
        
        # Test ping method raises NotImplementedError
        with pytest.raises(NotImplementedError):
            backend.ping(True)
        
        # Test _handle_error with NotImplementedError
        with pytest.raises(NotImplementedError):
            backend._handle_error(NotImplementedError("test"))
        
        # Test _handle_error with other error
        with pytest.raises(DatabaseError):
            backend._handle_error(ValueError("test"))
        
        # Test _get_cursor raises NotImplementedError
        with pytest.raises(NotImplementedError):
            backend._get_cursor()
        
        # Test _execute_query raises NotImplementedError
        with pytest.raises(NotImplementedError):
            backend._execute_query(None, "SELECT 1", None)
        
        # Test _handle_auto_commit (should not raise)
        backend._handle_auto_commit()
        
        # Test transaction_manager property raises NotImplementedError
        with pytest.raises(NotImplementedError):
            _ = backend.transaction_manager


class TestAsyncDummyBackendRemainingCoverage:
    """Tests for remaining uncovered lines in AsyncDummyBackend."""
    
    @pytest.mark.asyncio
    async def test_async_dummy_backend_all_methods(self):
        """Test all async methods to ensure coverage."""
        backend = AsyncDummyBackend()
        
        # Test _initialize_capabilities (covers line 94-96)
        capabilities = backend._initialize_capabilities()
        assert capabilities is not None
        
        # Test get_default_adapter_suggestions (covers related line)
        suggestions = backend.get_default_adapter_suggestions()
        assert suggestions == {}
        
        # Test dialect property
        dialect = backend.dialect
        assert dialect is not None
        
        # Test async connect method raises NotImplementedError
        with pytest.raises(NotImplementedError):
            await backend.connect()
        
        # Test async disconnect method (should not raise)
        await backend.disconnect()
        
        # Test async ping method raises NotImplementedError
        with pytest.raises(NotImplementedError):
            await backend.ping(True)
        
        # Test async _handle_error with NotImplementedError (covers line 124)
        with pytest.raises(NotImplementedError):
            await backend._handle_error(NotImplementedError("test"))
        
        # Test async _handle_error with other error
        with pytest.raises(DatabaseError):
            await backend._handle_error(ValueError("test"))
        
        # Test async _get_cursor raises NotImplementedError
        with pytest.raises(NotImplementedError):
            await backend._get_cursor()
        
        # Test async _execute_query raises NotImplementedError
        with pytest.raises(NotImplementedError):
            await backend._execute_query(None, "SELECT 1", None)
        
        # Test async _handle_auto_commit (should not raise)
        await backend._handle_auto_commit()
        
        # Test async transaction_manager property raises NotImplementedError (covers line 133)
        with pytest.raises(NotImplementedError):
            _ = backend.transaction_manager


class TestDummyDialectRemainingCoverage:
    """Tests for remaining uncovered branches in DummyDialect."""
    
    def test_dummy_dialect_all_methods(self):
        """Test all dialect methods to ensure branch coverage."""
        dialect = DummyDialect()
        
        # Test all the support methods to ensure all branches are covered
        methods_and_expected = [
            (dialect.supports_window_functions, True),
            (dialect.supports_window_frame_clause, True),
            (dialect.supports_basic_cte, True),
            (dialect.supports_recursive_cte, True),
            (dialect.supports_materialized_cte, True),
            (dialect.supports_rollup, True),
            (dialect.supports_cube, True),
            (dialect.supports_grouping_sets, True),
            (dialect.supports_returning_clause, True),
            (dialect.supports_upsert, True),
            (dialect.supports_lateral_join, True),
            (dialect.supports_array_type, True),
            (dialect.supports_array_constructor, True),
            (dialect.supports_array_access, True),
            (dialect.supports_json_type, True),
            (dialect.supports_json_table, True),
            (dialect.supports_explain_analyze, True),
            (dialect.supports_filter_clause, True),
            (dialect.supports_ordered_set_aggregation, True),
            (dialect.supports_merge_statement, True),
            (dialect.supports_temporal_tables, True),
            (dialect.supports_qualify_clause, True),
            (dialect.supports_for_update_skip_locked, True),
            (dialect.supports_graph_match, True),
        ]
        
        for method, expected in methods_and_expected:
            assert method() == expected
        
        # Test other methods
        assert dialect.get_upsert_syntax_type() == "ON CONFLICT"
        assert dialect.get_json_access_operator() == "->"
        assert dialect.supports_explain_format("ANY") is True
        assert dialect.name == "Dummy"