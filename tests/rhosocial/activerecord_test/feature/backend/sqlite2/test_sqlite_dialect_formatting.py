# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_dialect_formatting.py
"""
Supplementary tests for SQLiteDialect formatting methods
"""
import pytest
from unittest.mock import Mock
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

class TestSQLiteDialectFormatting:
    """Test SQLiteDialect formatting functionality"""

    def test_format_identifier(self):
        """Test identifier formatting"""
        dialect = SQLiteDialect()

        # Basic identifiers
        assert dialect.format_identifier("column_name") == '"column_name"'
        assert dialect.format_identifier("table") == '"table"'

        # Identifiers with quotes
        assert dialect.format_identifier('col"umn') == '"col""umn"'
        assert dialect.format_identifier('"quoted"') == '"""quoted"""'

    @pytest.mark.parametrize("identifier,expected", [
        ("simple", '"simple"'),
        ("with_space", '"with_space"'),
        ('with"quote', '"with""quote"'),
        ('"already"quoted"', '"""already""quoted"""'),
        ("with.dot", '"with.dot"'),
        ("with-dash", '"with-dash"'),
    ])
    def test_format_identifier_parametrized(self, identifier, expected):
        """Parametrized test for identifier formatting"""
        dialect = SQLiteDialect()
        result = dialect.format_identifier(identifier)
        assert result == expected

    def test_format_join_expression_right_join_error(self):
        """Test RIGHT JOIN formatting error"""
        dialect = SQLiteDialect()
        mock_join_expr = Mock()
        mock_join_expr.join_type = "RIGHT JOIN"

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            dialect.format_join_expression(mock_join_expr)

        assert "RIGHT JOIN" in str(exc_info.value)
        assert "SQLite does not support RIGHT JOIN or FULL OUTER JOIN" in str(exc_info.value)

    def test_format_join_expression_full_join_error(self):
        """Test FULL OUTER JOIN formatting error"""
        dialect = SQLiteDialect()
        mock_join_expr = Mock()
        mock_join_expr.join_type = "FULL OUTER JOIN"

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            dialect.format_join_expression(mock_join_expr)

        assert "FULL OUTER JOIN" in str(exc_info.value)
        assert "SQLite does not support RIGHT JOIN or FULL OUTER JOIN" in str(exc_info.value)

    def test_format_join_expression_full_outer_join_error(self):
        """Test FULL OUTER JOIN formatting error (alternative form)"""
        dialect = SQLiteDialect()
        mock_join_expr = Mock()
        mock_join_expr.join_type = "FULL OUTER JOIN"

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            dialect.format_join_expression(mock_join_expr)

        assert "FULL OUTER JOIN" in str(exc_info.value)

    @pytest.mark.parametrize("join_type", ["RIGHT JOIN", "FULL OUTER JOIN", "FULL JOIN"])
    def test_format_join_expression_unsupported_joins(self, join_type):
        """Parametrized test for unsupported JOIN types"""
        dialect = SQLiteDialect()
        mock_join_expr = Mock()
        mock_join_expr.join_type = join_type

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            dialect.format_join_expression(mock_join_expr)

        assert join_type in str(exc_info.value)

    def test_format_grouping_expression_rollup_error(self):
        """Test ROLLUP formatting error"""
        dialect = SQLiteDialect()
        mock_expressions = []

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            dialect.format_grouping_expression("ROLLUP", mock_expressions)

        assert "ROLLUP" in str(exc_info.value)
        assert "SQLite" in str(exc_info.value)

    def test_format_grouping_expression_cube_error(self):
        """Test CUBE formatting error"""
        dialect = SQLiteDialect()
        mock_expressions = []

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            dialect.format_grouping_expression("CUBE", mock_expressions)

        assert "CUBE" in str(exc_info.value)
        assert "SQLite" in str(exc_info.value)

    def test_format_grouping_expression_grouping_sets_error(self):
        """Test GROUPING SETS formatting error"""
        dialect = SQLiteDialect()
        mock_expressions = []

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            dialect.format_grouping_expression("GROUPING SETS", mock_expressions)

        assert "GROUPING SETS" in str(exc_info.value)
        assert "SQLite" in str(exc_info.value)

    @pytest.mark.parametrize("operation,expected_error_part", [
        ("ROLLUP", "ROLLUP"),
        ("CUBE", "CUBE"),
        ("GROUPING SETS", "GROUPING SETS"),
    ])
    def test_formatting_grouping_methods_unsupported(self, operation, expected_error_part):
        """Parametrized test for unsupported grouping formatting methods"""
        dialect = SQLiteDialect()

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            dialect.format_grouping_expression(operation, [])

        assert expected_error_part in str(exc_info.value)

    def test_format_array_expression_error(self):
        """Test array expression formatting error"""
        dialect = SQLiteDialect()

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            dialect.format_array_expression("operation", [], None, None)

        assert "Array operations" in str(exc_info.value)
        assert "SQLite does not support native array types" in str(exc_info.value)

    def test_format_json_table_expression_error(self):
        """Test JSON_TABLE expression formatting error"""
        dialect = SQLiteDialect()

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            dialect.format_json_table_expression("json_col", "$.path", [], "alias", ())

        assert "JSON_TABLE function" in str(exc_info.value)
        assert "SQLite does not support JSON_TABLE" in str(exc_info.value)

    def test_format_match_clause_error(self):
        """Test graph match clause formatting error"""
        dialect = SQLiteDialect()
        mock_clause = Mock()

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            dialect.format_match_clause(mock_clause)

        assert "graph MATCH clause" in str(exc_info.value)
        assert "SQLite does not support graph MATCH clause" in str(exc_info.value)

    def test_format_ordered_set_aggregation_error(self):
        """Test ordered-set aggregation formatting error"""
        dialect = SQLiteDialect()

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            dialect.format_ordered_set_aggregation("func", [], (), [], (), None)

        assert "ordered-set aggregate functions" in str(exc_info.value)
        assert "SQLite does not support ordered-set aggregate functions" in str(exc_info.value)

    def test_format_qualify_clause_error(self):
        """Test QUALIFY clause formatting error"""
        dialect = SQLiteDialect()
        mock_clause = Mock()

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            dialect.format_qualify_clause(mock_clause)

        assert "QUALIFY clause" in str(exc_info.value)
        assert "SQLite does not support QUALIFY clause" in str(exc_info.value)

    @pytest.mark.parametrize("operation,method_name,expected_error_part", [
        ("operation", "format_array_expression", "Array operations"),
        ("operation", "format_json_table_expression", "JSON_TABLE function"),
        ("operation", "format_match_clause", "graph MATCH clause"),
        ("operation", "format_ordered_set_aggregation", "ordered-set aggregate functions"),
        ("operation", "format_qualify_clause", "QUALIFY clause"),
    ])
    def test_formatting_methods_unsupported(self, operation, method_name, expected_error_part):
        """Parametrized test for unsupported formatting methods"""
        dialect = SQLiteDialect()
        method = getattr(dialect, method_name)

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            if method_name == "format_array_expression":
                method(operation, [], None, None)
            elif method_name == "format_json_table_expression":
                method("json_col", "$.path", [], "alias", ())
            elif method_name == "format_ordered_set_aggregation":
                method("func", [], (), [], (), None)
            else:
                mock_obj = Mock()
                method(mock_obj)

        assert expected_error_part in str(exc_info.value)

    def test_format_returning_clause_unsupported_error(self):
        """Test RETURNING clause formatting error (when unsupported)"""
        dialect = SQLiteDialect((3, 34, 0))  # Below version 3.35.0
        mock_clause = Mock()
        mock_clause.expressions = []
        mock_clause.alias = None

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            dialect.format_returning_clause(mock_clause)

        assert "RETURNING clause" in str(exc_info.value)
        assert "Use a separate SELECT statement" in str(exc_info.value)

    def test_format_returning_clause_supported(self):
        """Test RETURNING clause formatting (when supported)"""
        dialect = SQLiteDialect((3, 35, 0))  # Version 3.35.0 and above
        mock_expr = Mock()
        mock_expr.to_sql.return_value = ("id", ())
        mock_clause = Mock()
        mock_clause.expressions = [mock_expr]
        mock_clause.alias = None

        sql, params = dialect.format_returning_clause(mock_clause)

        assert sql == "RETURNING id"
        assert params == ()

    def test_format_returning_clause_with_alias(self):
        """Test RETURNING clause formatting with alias"""
        dialect = SQLiteDialect((3, 35, 0))
        mock_expr = Mock()
        mock_expr.to_sql.return_value = ("id", ())
        mock_clause = Mock()
        mock_clause.expressions = [mock_expr]
        mock_clause.alias = "result"

        sql, params = dialect.format_returning_clause(mock_clause)

        assert sql == 'RETURNING id AS "result"'
        assert params == ()

    def test_format_returning_clause_multiple_expressions(self):
        """Test RETURNING clause formatting with multiple expressions"""
        dialect = SQLiteDialect((3, 35, 0))
        mock_expr1 = Mock()
        mock_expr1.to_sql.return_value = ("id", ())
        mock_expr2 = Mock()
        mock_expr2.to_sql.return_value = ("name", ())
        mock_clause = Mock()
        mock_clause.expressions = [mock_expr1, mock_expr2]
        mock_clause.alias = None

        sql, params = dialect.format_returning_clause(mock_clause)

        assert sql == "RETURNING id, name"
        assert params == ()