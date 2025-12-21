# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_query_sources_json_table.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, Subquery, QueryExpression, TableExpression
)
from rhosocial.activerecord.backend.expression.query_sources import (
    JSONTableExpression, JSONTableColumn
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestJSONTableExpression:
    """Tests for JSONTableExpression representing JSON_TABLE function calls."""

    def test_json_table_basic(self, dummy_dialect: DummyDialect):
        """Test basic JSON_TABLE expression."""
        columns = [
            JSONTableColumn(name="id", data_type="INTEGER", path="$.id"),
            JSONTableColumn(name="name", data_type="VARCHAR(255)", path="$.name")
        ]
        
        json_table = JSONTableExpression(
            dummy_dialect,
            json_column="json_data",
            path="$[*]",  # Path to extract all elements
            columns=columns,
            alias="parsed_json"
        )
        
        sql, params = json_table.to_sql()
        
        assert "JSON_TABLE" in sql.upper()
        assert "parsed_json" in sql
        assert "id" in sql
        assert "name" in sql
        assert params == ()

    def test_json_table_with_column_object(self, dummy_dialect: DummyDialect):
        """Test JSON_TABLE with Column object as json_column."""
        json_col = Column(dummy_dialect, "json_field", table="my_table")
        columns = [
            JSONTableColumn(name="value", data_type="TEXT", path="$.value")
        ]
        
        json_table = JSONTableExpression(
            dummy_dialect,
            json_column=json_col,
            path="$.items[*]",
            columns=columns,
            alias="json_values"
        )
        
        sql, params = json_table.to_sql()
        
        assert "JSON_TABLE" in sql.upper()
        assert "json_values" in sql
        assert params == ()

    def test_json_table_multiple_columns(self, dummy_dialect: DummyDialect):
        """Test JSON_TABLE with multiple columns."""
        columns = [
            JSONTableColumn(name="user_id", data_type="INTEGER", path="$.userId"),
            JSONTableColumn(name="user_name", data_type="VARCHAR(100)", path="$.userName"),
            JSONTableColumn(name="active", data_type="BOOLEAN", path="$.isActive"),
            JSONTableColumn(name="score", data_type="DECIMAL(5,2)", path="$.score")
        ]
        
        json_table = JSONTableExpression(
            dummy_dialect,
            json_column="user_json",
            path="$",
            columns=columns,
            alias="user_data"
        )
        
        sql, params = json_table.to_sql()
        
        assert "JSON_TABLE" in sql.upper()
        assert "user_data" in sql
        assert "user_id" in sql
        assert "user_name" in sql
        assert "active" in sql
        assert "score" in sql
        assert params == ()

    def test_json_table_used_in_query(self, dummy_dialect: DummyDialect):
        """Test JSON_TABLE expression used in a query FROM clause."""
        columns = [
            JSONTableColumn(name="id", data_type="INTEGER", path="$.id"),
            JSONTableColumn(name="title", data_type="VARCHAR(200)", path="$.title")
        ]
        
        json_table = JSONTableExpression(
            dummy_dialect,
            json_column="json_content",
            path="$.articles[*]",
            columns=columns,
            alias="articles"
        )
        
        query = QueryExpression(
            dummy_dialect,
            select=[
                Column(dummy_dialect, "id", table="articles"),
                Column(dummy_dialect, "title", table="articles")
            ],
            from_=json_table
        )
        
        sql, params = query.to_sql()
        
        assert "JSON_TABLE" in sql.upper()
        assert "articles" in sql
        assert "id" in sql
        assert "title" in sql
        assert params == ()

    def test_json_table_with_table_reference(self, dummy_dialect: DummyDialect):
        """Test JSON_TABLE with table-referenced JSON column."""
        columns = [
            JSONTableColumn(name="field", data_type="TEXT", path="$.field"),
            JSONTableColumn(name="value", data_type="TEXT", path="$.value")
        ]

        json_table = JSONTableExpression(
            dummy_dialect,
            json_column=Column(dummy_dialect, "metadata", table="documents"),
            path="$.key_values[*]",
            columns=columns,
            alias="key_val_pairs"
        )

        # Use the JSON table directly in a query
        query = QueryExpression(
            dummy_dialect,
            select=[
                Column(dummy_dialect, "field", table="key_val_pairs"),
                Column(dummy_dialect, "value", table="key_val_pairs")
            ],
            from_=json_table
        )

        sql, params = query.to_sql()

        assert "JSON_TABLE" in sql.upper()
        assert "key_val_pairs" in sql
        assert params == ()

    def test_json_table_column_types_variety(self, dummy_dialect: DummyDialect):
        """Test JSON_TABLE with different column data types."""
        columns = [
            JSONTableColumn(name="int_col", data_type="INTEGER", path="$.intField"),
            JSONTableColumn(name="str_col", data_type="VARCHAR(255)", path="$.strField"),
            JSONTableColumn(name="bool_col", data_type="BOOLEAN", path="$.boolField"),
            JSONTableColumn(name="date_col", data_type="DATE", path="$.dateField"),
            JSONTableColumn(name="float_col", data_type="FLOAT", path="$.floatField")
        ]
        
        json_table = JSONTableExpression(
            dummy_dialect,
            json_column="mixed_json",
            path="$",
            columns=columns,
            alias="typed_columns"
        )
        
        sql, params = json_table.to_sql()
        
        assert "JSON_TABLE" in sql.upper()
        assert "typed_columns" in sql
        assert params == ()

    def test_json_table_complex_paths(self, dummy_dialect: DummyDialect):
        """Test JSON_TABLE with complex JSON paths."""
        columns = [
            JSONTableColumn(name="nested_value", data_type="TEXT", path="$.level1.level2.level3.value"),
            JSONTableColumn(name="array_element", data_type="INTEGER", path="$.array[0].id"),
            JSONTableColumn(name="dynamic_key", data_type="TEXT", path="$.*.dynamicValue")
        ]
        
        json_table = JSONTableExpression(
            dummy_dialect,
            json_column="complex_json",
            path="$",
            columns=columns,
            alias="complex_parsed"
        )
        
        sql, params = json_table.to_sql()
        
        assert "JSON_TABLE" in sql.upper()
        assert "complex_parsed" in sql
        assert params == ()

    def test_json_table_with_simple_string_column(self, dummy_dialect: DummyDialect):
        """Test JSON_TABLE with simple string column name."""
        columns = [
            JSONTableColumn(name="result", data_type="TEXT", path="$.result")
        ]
        
        json_table = JSONTableExpression(
            dummy_dialect,
            json_column="simple_json_col",  # Just a string column name
            path="$",
            columns=columns,
            alias="simple_result"
        )
        
        sql, params = json_table.to_sql()
        
        assert "JSON_TABLE" in sql.upper()
        assert "simple_result" in sql
        assert params == ()

    def test_json_table_empty_columns(self, dummy_dialect: DummyDialect):
        """Test JSON_TABLE with empty columns list."""
        json_table = JSONTableExpression(
            dummy_dialect,
            json_column="json_data",
            path="$",
            columns=[],
            alias="empty_cols"
        )
        
        sql, params = json_table.to_sql()
        
        assert "JSON_TABLE" in sql.upper()
        assert "empty_cols" in sql
        assert params == ()

    def test_json_table_column_attributes(self, dummy_dialect: DummyDialect):
        """Test that JSONTableColumn attributes are properly handled."""
        col = JSONTableColumn(name="test_col", data_type="VARCHAR(50)", path="$.test")
        
        # Verify the dataclass attributes
        assert col.name == "test_col"
        assert col.data_type == "VARCHAR(50)"
        assert col.path == "$.test"
        
        columns = [col]
        
        json_table = JSONTableExpression(
            dummy_dialect,
            json_column="test_json",
            path="$",
            columns=columns,
            alias="test_alias"
        )
        
        sql, params = json_table.to_sql()
        
        assert "JSON_TABLE" in sql.upper()
        assert "test_alias" in sql
        assert params == ()