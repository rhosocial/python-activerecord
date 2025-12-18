import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, RawSQLExpression, Subquery, QueryExpression, TableExpression
)
from rhosocial.activerecord.backend.expression.statements import InsertExpression
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

class TestInsertStatements:
    """Tests for INSERT statements with various configurations."""
    
    @pytest.mark.parametrize("table, columns, values_data_row, expected_sql_pattern, expected_param_count", [
        ("users", ["name", "email"], ["John Doe", "john@example.com"],
         'INSERT INTO "users" ("name", "email") VALUES (?, ?)', 2),

        ("products", ["id", "name", "price"], [1, "Widget", 19.99],
         'INSERT INTO "products" ("id", "name", "price") VALUES (?, ?, ?)', 3),
    ])
    def test_basic_insert(self, dummy_dialect: DummyDialect, table, columns, values_data_row, expected_sql_pattern, expected_param_count):
        """Tests basic INSERT statements with explicit columns and a single row of values."""
        # Create Literal values with dialect
        values_list_expr = [[Literal(dummy_dialect, val) for val in values_data_row]]

        insert_expr = InsertExpression(
            dummy_dialect,
            table=table,
            columns=columns,
            values_list=values_list_expr
        )
        sql, params = insert_expr.to_sql()
        assert sql == expected_sql_pattern
        assert len(params) == expected_param_count
        assert params == tuple(values_data_row)

    def test_insert_with_raw_sql_value(self, dummy_dialect: DummyDialect):
        """Tests INSERT statement with a value from a raw SQL expression."""
        insert_expr = InsertExpression(
            dummy_dialect,
            table="logs",
            columns=["event_time", "message"],
            values_list=[[RawSQLExpression(dummy_dialect, "CURRENT_TIMESTAMP"), Literal(dummy_dialect, "System started")]]
        )
        sql, params = insert_expr.to_sql()
        assert sql == 'INSERT INTO "logs" ("event_time", "message") VALUES (CURRENT_TIMESTAMP, ?)'
        assert params == ("System started",)

    def test_multi_row_insert_values(self, dummy_dialect: DummyDialect):
        """Tests INSERT with multiple rows using the VALUES clause."""
        bulk_values_data = [
            (1, "Product A", 10.0),
            (2, "Product B", 15.0),
            (3, "Product C", 20.0)
        ]
        columns = ["id", "name", "price"]
        values_list_expr = [[Literal(dummy_dialect, val) for val in row] for row in bulk_values_data]

        insert_expr = InsertExpression(
            dummy_dialect,
            table="products",
            columns=columns,
            values_list=values_list_expr
        )
        sql, params = insert_expr.to_sql()
        expected_sql = 'INSERT INTO "products" ("id", "name", "price") VALUES (?, ?, ?), (?, ?, ?), (?, ?, ?)'
        expected_params = (1, "Product A", 10.0, 2, "Product B", 15.0, 3, "Product C", 20.0)
        assert sql == expected_sql
        assert params == expected_params
    
    def test_insert_with_special_types(self, dummy_dialect: DummyDialect):
        """Tests INSERT with special data types like None, lists, etc."""
        insert_expr = InsertExpression(
            dummy_dialect,
            table="test_table",
            columns=["nullable_col", "array_col", "simple_col"],
            values_list=[[Literal(dummy_dialect, None), Literal(dummy_dialect, ["item1", "item2"]), Literal(dummy_dialect, "simple_value")]]
        )
        sql, params = insert_expr.to_sql()
        # Should contain placeholders for all values including NULL and arrays
        assert 'INSERT INTO "test_table" ("nullable_col", "array_col", "simple_col") VALUES (?, ?, ?)' == sql
        # The array might be expanded to individual items depending on the implementation
        assert params == (None, ["item1", "item2"], "simple_value")

    def test_insert_with_default_values_using_raw_sql(self, dummy_dialect: DummyDialect):
        """Tests INSERT with DEFAULT using RawSQLExpression to simulate default value assignment."""
        insert_expr = InsertExpression(
            dummy_dialect,
            table="users",
            columns=["name", "status"],  # Assuming 'status' has a default value in schema
            values_list=[[Literal(dummy_dialect, "John Doe"), RawSQLExpression(dummy_dialect, "DEFAULT")]]
        )
        sql, params = insert_expr.to_sql()
        # The implementation should handle RawSQLExpression as-is, so "DEFAULT" appears directly
        assert 'INSERT INTO "users" ("name", "status") VALUES (?, DEFAULT)' == sql
        # Only the parametrized value ("John Doe") should be in params
        assert params == ("John Doe",)

    def test_insert_omitting_primary_key_autoincrement(self, dummy_dialect: DummyDialect):
        """Tests INSERT when primary key column is omitted (auto-increment scenario)."""
        insert_expr = InsertExpression(
            dummy_dialect,
            table="products",
            columns=["name", "price"],  # Omitting the 'id' primary key column
            values_list=[[Literal(dummy_dialect, "New Product"), Literal(dummy_dialect, 29.99)]]
        )
        sql, params = insert_expr.to_sql()
        # The SQL should only include the specified columns, not the omitted primary key
        assert sql == 'INSERT INTO "products" ("name", "price") VALUES (?, ?)'
        assert params == ("New Product", 29.99)
        # The primary key would be automatically generated by the database
        assert '"id"' not in sql  # Primary key column should not appear in the INSERT statement

    def test_insert_default_values(self, dummy_dialect: DummyDialect):
        """Tests INSERT INTO <table> DEFAULT VALUES statement."""
        insert_expr = InsertExpression(
            dummy_dialect,
            table="settings",
            default_values=True
        )
        sql, params = insert_expr.to_sql()
        assert sql == 'INSERT INTO "settings" DEFAULT VALUES'
        assert params == ()

    def test_insert_select(self, dummy_dialect: DummyDialect):
        """Tests INSERT INTO <table> (cols) SELECT ... FROM ... statement."""
        select_query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "old_name"), Column(dummy_dialect, "old_email")],
            from_=TableExpression(dummy_dialect, "old_users"),
            where=Column(dummy_dialect, "status") == Literal(dummy_dialect, "active")
        )
        insert_expr = InsertExpression(
            dummy_dialect,
            table="new_users",
            columns=["name", "email"],
            select_query=select_query
        )
        sql, params = insert_expr.to_sql()
        expected_sql = 'INSERT INTO "new_users" ("name", "email") SELECT "old_name", "old_email" FROM "old_users" WHERE "status" = ?'
        assert sql == expected_sql
        assert params == ("active",)

    def test_insert_validation_multiple_methods(self, dummy_dialect: DummyDialect):
        """Tests that InsertExpression raises ValueError if multiple insertion methods are provided."""
        with pytest.raises(ValueError, match="Only one of 'values_list', 'select_query', or 'default_values' can be provided"):
            InsertExpression(
                dummy_dialect,
                table="test_table",
                columns=["col1"],
                values_list=[[Literal(dummy_dialect, 1)]],
                default_values=True
            )
        
        with pytest.raises(ValueError, match="Only one of 'values_list', 'select_query', or 'default_values' can be provided"):
            InsertExpression(
                dummy_dialect,
                table="test_table",
                columns=["col1"],
                values_list=[[Literal(dummy_dialect, 1)]],
                select_query=QueryExpression(dummy_dialect, select=[Literal(dummy_dialect, 1)])
            )
    
    def test_insert_validation_no_source_no_columns(self, dummy_dialect: DummyDialect):
        """Tests that InsertExpression raises ValueError if no insertion method and no columns are provided."""
        with pytest.raises(ValueError, match="At least one of 'values_list', 'select_query', or 'default_values' must be provided"):
            InsertExpression(
                dummy_dialect,
                table="test_table"
            )

    def test_insert_validation_select_query_without_columns(self, dummy_dialect: DummyDialect):
        """Tests that InsertExpression raises ValueError if select_query is used without specifying columns."""
        select_query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "data")]
        )
        insert_expr = InsertExpression(
            dummy_dialect,
            table="test_table",
            select_query=select_query
        )
        with pytest.raises(ValueError, match="Columns must be specified when using 'select_query' for INSERT."):
            insert_expr.to_sql()

    def test_insert_validation_values_list_without_columns(self, dummy_dialect: DummyDialect):
        """Tests that InsertExpression raises ValueError if values_list is used without specifying columns."""
        insert_expr = InsertExpression(
            dummy_dialect,
            table="test_table",
            values_list=[[Literal(dummy_dialect, 1)]]
        )
        with pytest.raises(ValueError, match="Columns must be specified when using 'values_list' for INSERT."):
            insert_expr.to_sql()

    def test_insert_validation_no_insertion_data_with_columns(self, dummy_dialect: DummyDialect):
        """Tests that InsertExpression raises ValueError if columns are provided but no insertion method is specified."""
        insert_expr = InsertExpression(
            dummy_dialect,
            table="test_table",
            columns=["col1", "col2"]
        )
        with pytest.raises(ValueError, match="No insertion data \(values_list, select_query, default_values\) provided."):
            insert_expr.to_sql()

    def test_insert_validation_invalid_state(self, dummy_dialect: DummyDialect):
        """Tests that InsertExpression raises ValueError for a completely invalid state (no data, no columns)."""
        with pytest.raises(ValueError, match="At least one of 'values_list', 'select_query', or 'default_values' must be provided for an INSERT statement, or columns must be specified for a SELECT subquery."):
            InsertExpression(
                dummy_dialect,
                table="test_table"
            )

    def test_insert_validation_default_values_with_columns(self, dummy_dialect: DummyDialect):
        """Tests that InsertExpression raises ValueError if default_values is true but columns are also provided."""
        insert_expr = InsertExpression(
            dummy_dialect,
            table="test_table",
            columns=["col1"],
            default_values=True
        )
        with pytest.raises(ValueError, match="Cannot use 'DEFAULT VALUES' with 'columns', 'values_list', or 'select_query'."):
            insert_expr.to_sql()
