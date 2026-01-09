# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_dialect_comprehensive.py
"""
Comprehensive supplementary tests for SQLiteDialect
"""
import pytest
from unittest.mock import Mock
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

class TestSQLiteDialectComprehensive:
    """Comprehensive tests for SQLiteDialect"""

    def test_init_with_default_version(self):
        """Test initialization with default version"""
        dialect = SQLiteDialect()
        assert dialect.get_server_version() == (3, 35, 0)  # Default version

    def test_init_with_custom_version(self):
        """Test initialization with custom version"""
        dialect = SQLiteDialect((3, 20, 1))
        assert dialect.get_server_version() == (3, 20, 1)

    def test_all_basic_methods(self):
        """Test consistency of all basic methods"""
        dialect = SQLiteDialect((3, 38, 0))

        # Test basic methods
        assert dialect.get_parameter_placeholder() == "?"
        assert dialect.get_server_version() == (3, 38, 0)
        assert dialect.get_json_access_operator() == "->"
        assert dialect.get_upsert_syntax_type() == "ON CONFLICT"

    @pytest.mark.parametrize("version,expected", [
        ((3, 7, 0), {"basic_cte": False, "recursive_cte": False}),
        ((3, 8, 3), {"basic_cte": True, "recursive_cte": True}),
        ((3, 25, 0), {"window_functions": True, "window_frame_clause": True}),
        ((3, 35, 0), {"returning_clause": True}),
        ((3, 38, 0), {"json_type": True}),
    ])
    def test_version_support_comprehensive(self, version, expected):
        """Comprehensive test for feature support across different versions"""
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
    def test_unsupported_features_comprehensive(self, method_name):
        """Comprehensive test for features that are always unsupported"""
        dialect = SQLiteDialect((3, 38, 0))  # Use latest version
        method = getattr(dialect, method_name)
        assert method() == False

    @pytest.mark.parametrize("operation,method_name,expected_error_part", [
        ("ROLLUP", "format_grouping_expression", "ROLLUP"),
        ("CUBE", "format_grouping_expression", "CUBE"),
        ("GROUPING SETS", "format_grouping_expression", "GROUPING SETS"),
        ("operation", "format_array_expression", "Array operations"),
        ("operation", "format_json_table_expression", "JSON_TABLE function"),
        ("operation", "format_match_clause", "graph MATCH clause"),
        ("operation", "format_ordered_set_aggregation", "ordered-set aggregate functions"),
        ("operation", "format_qualify_clause", "QUALIFY clause"),
    ])
    def test_formatting_methods_unsupported_comprehensive(self, operation, method_name, expected_error_part):
        """Comprehensive test for unsupported formatting methods"""
        dialect = SQLiteDialect()
        method = getattr(dialect, method_name)

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            if method_name == "format_grouping_expression":
                method(operation, [])
            elif method_name == "format_array_expression":
                method(operation, [], None, None)
            elif method_name == "format_json_table_expression":
                method("json_col", "$.path", [], "alias", ())
            elif method_name == "format_ordered_set_aggregation":
                method("func", [], (), [], (), None)
            else:
                mock_obj = Mock()
                method(mock_obj)

        assert expected_error_part in str(exc_info.value)

    @pytest.mark.parametrize("join_type", ["RIGHT JOIN", "FULL OUTER JOIN", "FULL JOIN"])
    def test_format_join_expression_unsupported_joins_comprehensive(self, join_type):
        """Comprehensive test for unsupported JOIN types"""
        dialect = SQLiteDialect()
        mock_join_expr = Mock()
        mock_join_expr.join_type = join_type

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            dialect.format_join_expression(mock_join_expr)

        expected_keyword = join_type.upper().split()[0]
        assert expected_keyword in str(exc_info.value)

    def test_format_returning_clause_version_check_comprehensive(self):
        """Comprehensive test for RETURNING clause version check"""
        # Below 3.35.0 version should raise exception
        dialect = SQLiteDialect((3, 34, 0))
        mock_clause = Mock()
        mock_clause.expressions = []
        mock_clause.alias = None

        with pytest.raises(UnsupportedFeatureError):
            dialect.format_returning_clause(mock_clause)

        # 3.35.0 and above should work normally
        dialect = SQLiteDialect((3, 35, 0))
        mock_expr = Mock()
        mock_expr.to_sql.return_value = ("id", ())
        mock_clause = Mock()
        mock_clause.expressions = [mock_expr]
        mock_clause.alias = None

        sql, params = dialect.format_returning_clause(mock_clause)
        assert sql == "RETURNING id"

    @pytest.mark.parametrize("identifier,expected", [
        ("simple", '"simple"'),
        ("with_space", '"with_space"'),
        ('with"quote', '"with""quote"'),
        ('"already"quoted"', '"""already""quoted"""'),
        ("with.dot", '"with.dot"'),
        ("with-dash", '"with-dash"'),
    ])
    def test_format_identifier_comprehensive(self, identifier, expected):
        """Comprehensive test for identifier formatting"""
        dialect = SQLiteDialect()
        result = dialect.format_identifier(identifier)
        assert result == expected

    def test_explain_format_case_insensitive(self):
        """Test EXPLAIN format support is case insensitive"""
        dialect = SQLiteDialect()

        # Test uppercase
        assert dialect.supports_explain_format("TEXT") == True
        assert dialect.supports_explain_format("DOT") == True

        # Test lowercase
        assert dialect.supports_explain_format("text") == True
        assert dialect.supports_explain_format("dot") == True

        # Test mixed case
        assert dialect.supports_explain_format("Text") == True
        assert dialect.supports_explain_format("Dot") == True