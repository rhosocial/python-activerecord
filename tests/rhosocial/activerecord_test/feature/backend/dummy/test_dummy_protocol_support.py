# tests/rhosocial/activerecord_test/feature/backend/dummy/test_dummy_protocol_support.py
"""
Tests for DummyDialect protocol support verification.

This test file verifies that DummyDialect implements all required protocols
and their support methods correctly. Since DummyDialect is designed to be
a full-featured SQL standard reference, all support methods should return True.
"""
import pytest
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestDummyProtocolSupport:
    """Test that DummyDialect correctly implements all protocol support methods."""

    @pytest.fixture
    def dialect(self):
        """Create a DummyDialect instance for testing."""
        return DummyDialect()

    # region Window Function Support
    def test_window_function_support_methods(self, dialect):
        """Test WindowFunctionSupport protocol methods."""
        assert dialect.supports_window_functions() is True
        assert dialect.supports_window_frame_clause() is True
    # endregion

    # region CTE Support
    def test_cte_support_methods(self, dialect):
        """Test CTESupport protocol methods."""
        assert dialect.supports_basic_cte() is True
        assert dialect.supports_recursive_cte() is True
        assert dialect.supports_materialized_cte() is True
    # endregion

    # region Advanced Grouping Support
    def test_advanced_grouping_support_methods(self, dialect):
        """Test AdvancedGroupingSupport protocol methods."""
        assert dialect.supports_rollup() is True
        assert dialect.supports_cube() is True
        assert dialect.supports_grouping_sets() is True
    # endregion

    # region Returning Support
    def test_returning_support_methods(self, dialect):
        """Test ReturningSupport protocol methods."""
        assert dialect.supports_returning_clause() is True
    # endregion

    # region Upsert Support
    def test_upsert_support_methods(self, dialect):
        """Test UpsertSupport protocol methods."""
        assert dialect.supports_upsert() is True
        assert dialect.get_upsert_syntax_type() == "ON CONFLICT"
    # endregion

    # region Lateral Join Support
    def test_lateral_join_support_methods(self, dialect):
        """Test LateralJoinSupport protocol methods."""
        assert dialect.supports_lateral_join() is True
    # endregion

    # region Array Support
    def test_array_support_methods(self, dialect):
        """Test ArraySupport protocol methods."""
        assert dialect.supports_array_type() is True
        assert dialect.supports_array_constructor() is True
        assert dialect.supports_array_access() is True
    # endregion

    # region JSON Support
    def test_json_support_methods(self, dialect):
        """Test JSONSupport protocol methods."""
        assert dialect.supports_json_type() is True
        assert dialect.get_json_access_operator() == "->"
        assert dialect.supports_json_table() is True
    # endregion

    # region Explain Support
    def test_explain_support_methods(self, dialect):
        """Test ExplainSupport protocol methods."""
        assert dialect.supports_explain_analyze() is True
        assert dialect.supports_explain_format("JSON") is True
        assert dialect.supports_explain_format("TEXT") is True
    # endregion

    # region Filter Clause Support
    def test_filter_clause_support_methods(self, dialect):
        """Test FilterClauseSupport protocol methods."""
        assert dialect.supports_filter_clause() is True
    # endregion

    # region Ordered Set Aggregation Support
    def test_ordered_set_aggregation_support_methods(self, dialect):
        """Test OrderedSetAggregationSupport protocol methods."""
        assert dialect.supports_ordered_set_aggregation() is True
    # endregion

    # region Merge Support
    def test_merge_support_methods(self, dialect):
        """Test MergeSupport protocol methods."""
        assert dialect.supports_merge_statement() is True
    # endregion

    # region Temporal Table Support
    def test_temporal_table_support_methods(self, dialect):
        """Test TemporalTableSupport protocol methods."""
        assert dialect.supports_temporal_tables() is True
    # endregion

    # region Qualify Clause Support
    def test_qualify_clause_support_methods(self, dialect):
        """Test QualifyClauseSupport protocol methods."""
        assert dialect.supports_qualify_clause() is True
    # endregion

    # region Locking Support
    def test_locking_support_methods(self, dialect):
        """Test LockingSupport protocol methods."""
        assert dialect.supports_for_update_skip_locked() is True
    # endregion

    # region Graph Support
    def test_graph_support_methods(self, dialect):
        """Test GraphSupport protocol methods."""
        assert dialect.supports_graph_match() is True
    # endregion

    # region Join Support
    def test_join_support_methods(self, dialect):
        """Test JoinSupport protocol methods."""
        assert dialect.supports_inner_join() is True
        assert dialect.supports_left_join() is True
        assert dialect.supports_right_join() is True
        assert dialect.supports_full_join() is True
        assert dialect.supports_cross_join() is True
        assert dialect.supports_natural_join() is True
    # endregion

    # region Set Operation Support
    def test_set_operation_support_methods(self, dialect):
        """Test SetOperationSupport protocol methods."""
        assert dialect.supports_union() is True
        assert dialect.supports_union_all() is True
        assert dialect.supports_intersect() is True
        assert dialect.supports_except() is True
        assert dialect.supports_set_operation_order_by() is True
        assert dialect.supports_set_operation_limit_offset() is True
        assert dialect.supports_set_operation_for_update() is True
    # endregion

    # region ILIKE Support
    def test_ilike_support_methods(self, dialect):
        """Test ILIKESupport protocol methods."""
        assert dialect.supports_ilike() is True
    # endregion

    # region Table DDL Support
    def test_table_support_methods(self, dialect):
        """Test TableSupport protocol methods."""
        assert dialect.supports_create_table() is True
        assert dialect.supports_drop_table() is True
        assert dialect.supports_alter_table() is True
        assert dialect.supports_temporary_table() is True
        assert dialect.supports_if_not_exists_table() is True
        assert dialect.supports_if_exists_table() is True
        assert dialect.supports_table_partitioning() is True
        assert dialect.supports_table_tablespace() is True
        assert dialect.supports_drop_column() is True
        assert dialect.supports_alter_column_type() is True
        assert dialect.supports_rename_column() is True
        assert dialect.supports_rename_table() is True
        assert dialect.supports_add_constraint() is True
        assert dialect.supports_drop_constraint() is True
    # endregion

    # region View DDL Support
    def test_view_support_methods(self, dialect):
        """Test ViewSupport protocol methods."""
        assert dialect.supports_create_view() is True
        assert dialect.supports_drop_view() is True
        assert dialect.supports_or_replace_view() is True
        assert dialect.supports_temporary_view() is True
        assert dialect.supports_materialized_view() is True
        assert dialect.supports_refresh_materialized_view() is True
        assert dialect.supports_materialized_view_tablespace() is True
        assert dialect.supports_materialized_view_storage_options() is True
        assert dialect.supports_if_exists_view() is True
        assert dialect.supports_view_check_option() is True
        assert dialect.supports_cascade_view() is True
    # endregion

    # region Truncate DDL Support
    def test_truncate_support_methods(self, dialect):
        """Test TruncateSupport protocol methods."""
        assert dialect.supports_truncate() is True
        assert dialect.supports_truncate_table_keyword() is True
        assert dialect.supports_truncate_restart_identity() is True
        assert dialect.supports_truncate_cascade() is True
    # endregion

    # region Schema DDL Support
    def test_schema_support_methods(self, dialect):
        """Test SchemaSupport protocol methods."""
        assert dialect.supports_create_schema() is True
        assert dialect.supports_drop_schema() is True
        assert dialect.supports_schema_if_not_exists() is True
        assert dialect.supports_schema_if_exists() is True
        assert dialect.supports_schema_cascade() is True
        assert dialect.supports_schema_authorization() is True
    # endregion

    # region Index DDL Support
    def test_index_support_methods(self, dialect):
        """Test IndexSupport protocol methods."""
        assert dialect.supports_create_index() is True
        assert dialect.supports_drop_index() is True
        assert dialect.supports_unique_index() is True
        assert dialect.supports_index_if_not_exists() is True
        assert dialect.supports_index_if_exists() is True
        assert dialect.supports_index_type() is True
        assert dialect.supports_partial_index() is True
        assert dialect.supports_functional_index() is True
        assert dialect.supports_index_include() is True
        assert dialect.supports_index_tablespace() is True
        assert dialect.supports_concurrent_index() is True
        # Check supported index types
        index_types = dialect.get_supported_index_types()
        assert isinstance(index_types, list)
        assert len(index_types) > 0
        assert 'BTREE' in index_types

    def test_fulltext_index_support_methods(self, dialect):
        """Test FULLTEXT index support methods."""
        assert dialect.supports_fulltext_index() is True
        assert dialect.supports_fulltext_parser() is True
        assert dialect.supports_fulltext_boolean_mode() is True
        assert dialect.supports_fulltext_query_expansion() is True
        # endregion

    # region Sequence DDL Support
    def test_sequence_support_methods(self, dialect):
        """Test SequenceSupport protocol methods."""
        assert dialect.supports_sequence() is True
        assert dialect.supports_create_sequence() is True
        assert dialect.supports_drop_sequence() is True
        assert dialect.supports_alter_sequence() is True
        assert dialect.supports_sequence_if_not_exists() is True
        assert dialect.supports_sequence_if_exists() is True
        assert dialect.supports_sequence_cycle() is True
        assert dialect.supports_sequence_cache() is True
        assert dialect.supports_sequence_order() is True
        assert dialect.supports_sequence_owned_by() is True
    # endregion

    # region Trigger DDL Support
    def test_trigger_support_methods(self, dialect):
        """Test TriggerSupport protocol methods."""
        assert dialect.supports_trigger() is True
        assert dialect.supports_create_trigger() is True
        assert dialect.supports_drop_trigger() is True
        assert dialect.supports_instead_of_trigger() is True
        assert dialect.supports_statement_trigger() is True
        assert dialect.supports_trigger_referencing() is True
        assert dialect.supports_trigger_when() is True
        assert dialect.supports_trigger_if_not_exists() is True
    # endregion

    # region Function DDL Support
    def test_function_support_methods(self, dialect):
        """Test FunctionSupport protocol methods."""
        assert dialect.supports_function() is True
        assert dialect.supports_create_function() is True
        assert dialect.supports_drop_function() is True
        assert dialect.supports_function_or_replace() is True
        assert dialect.supports_function_parameters() is True
    # endregion


class TestDummyProtocolCompleteness:
    """Test that all protocols are properly implemented by DummyDialect."""

    @pytest.fixture
    def dialect(self):
        """Create a DummyDialect instance for testing."""
        return DummyDialect()

    def test_dialect_implements_all_protocols(self, dialect):
        """Verify DummyDialect implements all expected protocols."""
        from rhosocial.activerecord.backend.dialect.protocols import (
            WindowFunctionSupport, CTESupport, AdvancedGroupingSupport,
            ReturningSupport, UpsertSupport, LateralJoinSupport,
            ArraySupport, JSONSupport, ExplainSupport,
            FilterClauseSupport, OrderedSetAggregationSupport, MergeSupport,
            TemporalTableSupport, QualifyClauseSupport, LockingSupport,
            GraphSupport, JoinSupport, SetOperationSupport,
            # DDL Protocols
            TableSupport, ViewSupport, TruncateSupport, SchemaSupport,
            IndexSupport, SequenceSupport, TriggerSupport, FunctionSupport,
            ILIKESupport,
        )

        # Verify all protocols are implemented
        assert isinstance(dialect, WindowFunctionSupport)
        assert isinstance(dialect, CTESupport)
        assert isinstance(dialect, AdvancedGroupingSupport)
        assert isinstance(dialect, ReturningSupport)
        assert isinstance(dialect, UpsertSupport)
        assert isinstance(dialect, LateralJoinSupport)
        assert isinstance(dialect, ArraySupport)
        assert isinstance(dialect, JSONSupport)
        assert isinstance(dialect, ExplainSupport)
        assert isinstance(dialect, FilterClauseSupport)
        assert isinstance(dialect, OrderedSetAggregationSupport)
        assert isinstance(dialect, MergeSupport)
        assert isinstance(dialect, TemporalTableSupport)
        assert isinstance(dialect, QualifyClauseSupport)
        assert isinstance(dialect, LockingSupport)
        assert isinstance(dialect, GraphSupport)
        assert isinstance(dialect, JoinSupport)
        assert isinstance(dialect, SetOperationSupport)
        assert isinstance(dialect, ILIKESupport)
        # DDL Protocols
        assert isinstance(dialect, TableSupport)
        assert isinstance(dialect, ViewSupport)
        assert isinstance(dialect, TruncateSupport)
        assert isinstance(dialect, SchemaSupport)
        assert isinstance(dialect, IndexSupport)
        assert isinstance(dialect, SequenceSupport)
        assert isinstance(dialect, TriggerSupport)
        assert isinstance(dialect, FunctionSupport)

    def test_dialect_implements_all_runtime_checkable_protocols(self, dialect):
        """Verify DummyDialect implements ALL @runtime_checkable protocols defined in protocols.py.

        This test dynamically discovers all protocols marked with @runtime_checkable
        in the protocols module, ensuring no protocol is accidentally omitted.

        If this test fails, it means a new protocol was added to protocols.py but
        DummyDialect was not updated to implement it.
        """
        import inspect
        from typing import Protocol
        from rhosocial.activerecord.backend import dialect as dialect_module

        # Find all @runtime_checkable Protocol classes in protocols module
        protocols_module = dialect_module.protocols

        all_protocols = []
        for name, obj in inspect.getmembers(protocols_module, inspect.isclass):
            # Check if it's a Protocol with @runtime_checkable
            if (
                hasattr(obj, '__protocol__') or  # Protocol classes have this
                (hasattr(obj, '__mro__') and Protocol in obj.__mro__ and
                 hasattr(obj, '__runtime_checkable__'))
            ):
                # Exclude Protocol base class itself and any private classes
                if obj is not Protocol and not name.startswith('_'):
                    all_protocols.append((name, obj))

        # Verify DummyDialect implements each discovered protocol
        missing_protocols = []
        for protocol_name, protocol_class in all_protocols:
            if not isinstance(dialect, protocol_class):
                missing_protocols.append(protocol_name)

        # Assert no protocols are missing
        assert len(missing_protocols) == 0, (
            f"DummyDialect is missing implementation for protocols: {missing_protocols}. "
            f"Please update DummyDialect to inherit from these protocols and implement "
            f"their required methods, then update supports_* methods to return True."
        )
