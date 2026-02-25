"""
Test suite to cover all branches in DummyDialect.
"""
import pytest
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestDummyDialectBranches:
    """Tests for all branches in DummyDialect to ensure 100% coverage."""
    
    def test_dummy_dialect_all_methods_called(self):
        """Test that all methods in DummyDialect are called to cover all branches."""
        dialect = DummyDialect()
        
        # Call all supports_* methods to cover all branches
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
        
        # Test that the dialect has a name property
        assert dialect.name == "Dummy"