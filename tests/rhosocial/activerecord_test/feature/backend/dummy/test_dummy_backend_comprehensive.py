"""
Comprehensive test suite for DummyBackend to achieve 100% coverage.
This includes tests for uncovered lines and branches in backend.py and dialect.py.
"""
import logging
from unittest.mock import Mock
import pytest
from rhosocial.activerecord.backend.impl.dummy.backend import DummyBackend, AsyncDummyBackend
from rhosocial.activerecord.backend.config import ConnectionConfig
from rhosocial.activerecord.backend.errors import DatabaseError
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestDummyBackendComprehensive:
    """Tests for uncovered lines and branches in DummyBackend."""

    def test_dummy_backend_with_logger_param(self):
        """Test DummyBackend constructor when logger is provided in kwargs."""
        logger = logging.getLogger('test_logger')
        backend = DummyBackend(logger=logger)
        assert backend.logger == logger

    def test_dummy_backend_handle_error_with_not_implemented_error(self):
        """Test _handle_error with NotImplementedError."""
        backend = DummyBackend()
        error = NotImplementedError("Test error")
        with pytest.raises(NotImplementedError):
            backend._handle_error(error)

    def test_dummy_backend_handle_error_with_other_error(self):
        """Test _handle_error with non-NotImplementedError."""
        backend = DummyBackend()
        error = ValueError("Test error")
        with pytest.raises(DatabaseError):
            backend._handle_error(error)

    def test_dummy_backend_get_server_version(self):
        """Test get_server_version returns correct dummy version."""
        backend = DummyBackend()
        version = backend.get_server_version()
        assert version == (0, 0, 0)


    def test_async_dummy_backend_initialization(self):
        """Test AsyncDummyBackend can be initialized."""
        backend = AsyncDummyBackend()
        # Should be able to initialize without error
        assert backend is not None

    def test_async_dummy_backend_get_default_adapter_suggestions(self):
        """Test AsyncDummyBackend get_default_adapter_suggestions."""
        backend = AsyncDummyBackend()
        suggestions = backend.get_default_adapter_suggestions()
        # Should return empty dict
        assert suggestions == {}

    def test_async_dummy_backend_dialect_property(self):
        """Test AsyncDummyBackend dialect property."""
        backend = AsyncDummyBackend()
        dialect = backend.dialect
        assert isinstance(dialect, DummyDialect)

    @pytest.mark.asyncio
    async def test_async_dummy_backend_connect_method(self):
        """Test AsyncDummyBackend connect method raises NotImplementedError."""
        backend = AsyncDummyBackend()
        with pytest.raises(NotImplementedError) as excinfo:
            await backend.connect()
        assert "does not support real database operations" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_async_dummy_backend_disconnect_method(self):
        """Test AsyncDummyBackend disconnect method."""
        backend = AsyncDummyBackend()
        # Should not raise any exception
        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_async_dummy_backend_ping_method(self):
        """Test AsyncDummyBackend ping method raises NotImplementedError."""
        backend = AsyncDummyBackend()
        with pytest.raises(NotImplementedError) as excinfo:
            await backend.ping()
        assert "does not support real database operations" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_async_dummy_backend_handle_error_method(self):
        """Test AsyncDummyBackend _handle_error method."""
        backend = AsyncDummyBackend()

        # Test with NotImplementedError
        error = NotImplementedError("Test error")
        with pytest.raises(NotImplementedError):
            await backend._handle_error(error)

        # Test with other error
        error = ValueError("Test error")
        with pytest.raises(DatabaseError):
            await backend._handle_error(error)

    def test_async_dummy_backend_transaction_manager_property(self):
        """Test AsyncDummyBackend transaction_manager property raises NotImplementedError."""
        backend = AsyncDummyBackend()
        with pytest.raises(NotImplementedError) as excinfo:
            _ = backend.transaction_manager
        assert "does not support real database operations" in str(excinfo.value)


class TestDummyDialectComprehensive:
    """Tests for all support methods in DummyDialect to ensure 100% coverage."""
    
    def test_dummy_dialect_all_support_methods_return_true(self):
        """Test that all supports_* methods in DummyDialect return True."""
        dialect = DummyDialect()

        # Test all the support methods return True
        assert dialect.supports_window_functions() is True
        assert dialect.supports_window_frame_clause() is True
        assert dialect.supports_basic_cte() is True
        assert dialect.supports_recursive_cte() is True
        assert dialect.supports_materialized_cte() is True
        assert dialect.supports_rollup() is True
        assert dialect.supports_cube() is True
        assert dialect.supports_grouping_sets() is True
        assert dialect.supports_returning_clause() is True
        assert dialect.supports_upsert() is True
        assert dialect.supports_lateral_join() is True
        assert dialect.supports_array_type() is True
        assert dialect.supports_array_constructor() is True
        assert dialect.supports_array_access() is True
        assert dialect.supports_json_type() is True
        assert dialect.supports_json_table() is True
        assert dialect.supports_explain_analyze() is True
        assert dialect.supports_filter_clause() is True
        assert dialect.supports_ordered_set_aggregation() is True
        assert dialect.supports_merge_statement() is True
        assert dialect.supports_temporal_tables() is True
        assert dialect.supports_qualify_clause() is True
        assert dialect.supports_for_update_skip_locked() is True
        assert dialect.supports_graph_match() is True

        # Test other methods
        assert dialect.get_upsert_syntax_type() == "ON CONFLICT"
        assert dialect.get_json_access_operator() == "->"
        assert dialect.supports_explain_format("ANY") is True