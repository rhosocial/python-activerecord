# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_dialect_version_support.py
"""
Supplementary tests for SQLiteDialect version support functionality
"""
import pytest
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

class TestSQLiteDialectVersionSupport:
    """Test SQLiteDialect version support functionality"""

    def test_version_3_8_0_features(self):
        """Test feature support for version 3.8.0"""
        dialect = SQLiteDialect((3, 8, 0))
        assert dialect.supports_basic_cte() == False
        assert dialect.supports_recursive_cte() == False
        assert dialect.supports_window_functions() == False
        assert dialect.supports_returning_clause() == False
        assert dialect.supports_filter_clause() == False
        assert dialect.supports_json_type() == False
        assert dialect.supports_upsert() == False

    def test_version_3_8_3_features(self):
        """Test feature support for version 3.8.3 (CTE support starts)"""
        dialect = SQLiteDialect((3, 8, 3))
        assert dialect.supports_basic_cte() == True
        assert dialect.supports_recursive_cte() == True
        assert dialect.supports_window_functions() == False
        assert dialect.supports_returning_clause() == False
        assert dialect.supports_filter_clause() == False
        assert dialect.supports_json_type() == False
        assert dialect.supports_upsert() == False

    def test_version_3_10_0_features(self):
        """Test feature support for version 3.10.0 (FILTER clause)"""
        dialect = SQLiteDialect((3, 10, 0))
        assert dialect.supports_filter_clause() == True
        assert dialect.supports_window_functions() == False
        assert dialect.supports_returning_clause() == False
        assert dialect.supports_json_type() == False
        assert dialect.supports_upsert() == False

    def test_version_3_24_0_features(self):
        """Test feature support for version 3.24.0 (UPSERT)"""
        dialect = SQLiteDialect((3, 24, 0))
        assert dialect.supports_upsert() == True
        assert dialect.get_upsert_syntax_type() == "ON CONFLICT"
        assert dialect.supports_window_functions() == False
        assert dialect.supports_returning_clause() == False
        assert dialect.supports_json_type() == False

    def test_version_3_25_0_features(self):
        """Test feature support for version 3.25.0 (window functions)"""
        dialect = SQLiteDialect((3, 25, 0))
        assert dialect.supports_window_functions() == True
        assert dialect.supports_window_frame_clause() == True
        assert dialect.supports_returning_clause() == False
        assert dialect.supports_json_type() == False

    def test_version_3_35_0_features(self):
        """Test feature support for version 3.35.0 (RETURNING clause)"""
        dialect = SQLiteDialect((3, 35, 0))
        assert dialect.supports_returning_clause() == True
        assert dialect.supports_json_type() == False

    def test_version_3_38_0_features(self):
        """Test feature support for version 3.38.0 (JSON)"""
        dialect = SQLiteDialect((3, 38, 0))
        assert dialect.supports_json_type() == True
        assert dialect.get_json_access_operator() == "->"

    def test_unsupported_features_always_false(self):
        """Test features that are always unsupported"""
        dialect = SQLiteDialect((3, 38, 0))
        assert dialect.supports_materialized_cte() == False
        assert dialect.supports_rollup() == False
        assert dialect.supports_cube() == False
        assert dialect.supports_grouping_sets() == False
        assert dialect.supports_array_type() == False
        assert dialect.supports_array_constructor() == False
        assert dialect.supports_array_access() == False
        assert dialect.supports_graph_match() == False
        assert dialect.supports_merge_statement() == False
        assert dialect.supports_temporal_tables() == False
        assert dialect.supports_qualify_clause() == False
        assert dialect.supports_ordered_set_aggregation() == False
        assert dialect.supports_json_table() == False

    @pytest.mark.parametrize("version,expected", [
        ((3, 7, 0), {"basic_cte": False, "recursive_cte": False}),
        ((3, 8, 3), {"basic_cte": True, "recursive_cte": True}),
        ((3, 25, 0), {"window_functions": True, "window_frame_clause": True}),
        ((3, 35, 0), {"returning_clause": True}),
        ((3, 38, 0), {"json_type": True}),
    ])
    def test_version_support_parametrized(self, version, expected):
        """参数化测试不同版本的特性支持"""
        dialect = SQLiteDialect(version)
        
        for feature, expected_value in expected.items():
            if feature == "basic_cte":
                assert dialect.supports_basic_cte() == expected_value
            elif feature == "recursive_cte":
                assert dialect.supports_recursive_cte() == expected_value
            elif feature == "window_functions":
                assert dialect.supports_window_functions() == expected_value
            elif feature == "window_frame_clause":
                assert dialect.supports_window_frame_clause() == expected_value
            elif feature == "returning_clause":
                assert dialect.supports_returning_clause() == expected_value
            elif feature == "json_type":
                assert dialect.supports_json_type() == expected_value

    @pytest.mark.parametrize("method_name", [
        "supports_materialized_cte",
        "supports_rollup", 
        "supports_cube",
        "supports_grouping_sets",
        "supports_array_type",
        "supports_array_constructor",
        "supports_array_access",
        "supports_graph_match",
        "supports_merge_statement", 
        "supports_temporal_tables",
        "supports_qualify_clause",
        "supports_ordered_set_aggregation",
        "supports_json_table",
    ])
    def test_unsupported_features_parametrized(self, method_name):
        """参数化测试始终不支持的特性"""
        dialect = SQLiteDialect((3, 38, 0))  # 使用最新版本
        method = getattr(dialect, method_name)
        assert method() == False