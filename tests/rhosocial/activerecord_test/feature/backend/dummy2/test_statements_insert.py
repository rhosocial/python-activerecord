# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_insert.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, RawSQLExpression, QueryExpression, TableExpression,
    InsertExpression, ValuesSource, SelectSource, DefaultValuesSource, OnConflictClause
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression.statements import InsertDataSource

class TestInsertStatements:
    """Tests for the refactored INSERT statement expressions."""

    def test_insert_data_source_dialect_property(self, dummy_dialect: DummyDialect):
        """Tests that InsertDataSource.dialect returns the correct dialect."""
        source = ValuesSource(dummy_dialect, values_list=[
            [Literal(dummy_dialect, "John Doe")]
        ])
        assert source.dialect is dummy_dialect

    def test_values_source_init_error_empty_values_list(self, dummy_dialect: DummyDialect):
        """Tests ValuesSource __init__ raises ValueError for empty or invalid values_list."""
        with pytest.raises(ValueError, match="'values_list' must be a non-empty list of lists."):
            ValuesSource(dummy_dialect, values_list=[])
        with pytest.raises(ValueError, match="'values_list' must be a non-empty list of lists."):
            ValuesSource(dummy_dialect, values_list=[Literal(dummy_dialect, "invalid")]) # Not a list of lists

    def test_values_source_init_error_row_length_mismatch(self, dummy_dialect: DummyDialect):
        """Tests ValuesSource __init__ raises ValueError for values_list with inconsistent row lengths."""
        with pytest.raises(ValueError, match="All rows in 'values_list' must have the same number of columns."):
            ValuesSource(dummy_dialect, values_list=[
                [Literal(dummy_dialect, "col1")],
                [Literal(dummy_dialect, "col2"), Literal(dummy_dialect, "col3")]
            ])

    @pytest.mark.parametrize("conflict_options, error_message", [
        pytest.param(
            dict(do_nothing=True, update_assignments={"name": "test_val"}), # Using a placeholder for Literal value
            "Cannot specify both 'do_nothing=True' and 'update_assignments' for ON CONFLICT.",
            id="do_nothing_with_update"
        ),
        pytest.param(
            dict(do_nothing=False, update_assignments=None),
            "Must specify either 'do_nothing=True' or 'update_assignments' for ON CONFLICT.",
            id="no_action_specified"
        ),
    ])
    def test_on_conflict_clause_init_errors(self, dummy_dialect: DummyDialect, conflict_options, error_message):
        """Tests validation errors in OnConflictClause.__init__."""
        # The Literal needs a dialect, so we assign it here if present
        if conflict_options.get("update_assignments"):
            # Create Literal objects for assignment values using the dialect
            conflict_options["update_assignments"] = {
                k: Literal(dummy_dialect, v) for k, v in conflict_options["update_assignments"].items()
            }

        with pytest.raises(ValueError, match=error_message):
            OnConflictClause(
                dummy_dialect,
                conflict_target=["id"],
                **conflict_options
            )

    # The original test for InsertExpression validation:
    # This test (test_insert_validation_error_on_conflict_with_default_values)
    # correctly triggers the first validation branch in InsertExpression.__init__:
    # "if isinstance(source, DefaultValuesSource) and (columns or on_conflict):"
    # The second validation branch remains unreachable with current InsertDataSource hierarchy.

    @pytest.mark.parametrize(
        "into_param, columns_param, returning_param, on_conflict_param, num_rows, expected_sql, expected_params",
        [
            # --- Single row inserts ---
            # Basic insert with str table, columns, no returning, no conflict
            pytest.param("users", ["name", "email"], None, None, 1,
             'INSERT INTO "users" ("name", "email") VALUES (?, ?)',
             ("John Doe", "john@example.com"), id="single_row_basic_insert"),
            # Basic insert with TableExpression, columns, no returning, no conflict
            pytest.param(TableExpression(None, "products", alias="p"), ["product_name"], None, None, 1,
             'INSERT INTO "products" AS "p" ("product_name") VALUES (?)',
             ("Laptop",), id="single_row_table_expr_insert"),
            # Insert with columns=None (valid for ValuesSource)
            pytest.param("log_events", None, None, None, 1,
             'INSERT INTO "log_events"  VALUES (?)',
             ("event_data",), id="single_row_insert_columns_none"),
            # Insert with returning
            pytest.param("orders", ["amount"], [Column(None, "id")], None, 1,
             'INSERT INTO "orders" ("amount") VALUES (?) RETURNING "id"',
             (100.50,), id="single_row_insert_returning"),
            # Insert with on_conflict DO NOTHING
            pytest.param("items", ["item_id"], None,
             OnConflictClause(None, conflict_target=["item_id"], do_nothing=True), 1,
             'INSERT INTO "items" ("item_id") VALUES (?) ON CONFLICT ("item_id") DO NOTHING',
             (10,), id="single_row_insert_on_conflict_do_nothing"),
            # Insert with on_conflict DO UPDATE
            pytest.param("metrics", ["key", "value"], None,
             OnConflictClause(None, conflict_target=["key"],
                              update_assignments={"value": Column(None, "value", "excluded")}), 1,
             'INSERT INTO "metrics" ("key", "value") VALUES (?, ?) ON CONFLICT ("key") DO UPDATE SET "value" = "excluded"."value"',
             ("cpu_usage", 85.5), id="single_row_insert_on_conflict_do_update"),

            # --- Multi row inserts ---
            # Multi-row with str table, columns, no returning, no conflict
            pytest.param("users", ["name", "email"], None, None, 2,
             'INSERT INTO "users" ("name", "email") VALUES (?, ?), (?, ?)',
             ("Jane Doe", "jane@example.com", "Peter Pan", "peter@example.com"), id="multi_row_basic_insert"),
            # Multi-row with TableExpression, columns, returning
            pytest.param(TableExpression(None, "transactions", alias="t"), ["txn_id", "status"], [Column(None, "id")], None, 2,
             'INSERT INTO "transactions" AS "t" ("txn_id", "status") VALUES (?, ?), (?, ?) RETURNING "id"',
             ("TXN001", "success", "TXN002", "pending"), id="multi_row_table_expr_insert_returning"),
            # Multi-row with on_conflict DO UPDATE with WHERE
            pytest.param("products", ["p_id", "qty"], None,
             OnConflictClause(None, conflict_target=["p_id"],
                              update_assignments={"qty": RawSQLExpression(None, "excluded.qty")},
                              update_where=Column(None, "qty", "products") < RawSQLExpression(None, "excluded.qty")), 2,
             'INSERT INTO "products" ("p_id", "qty") VALUES (?, ?), (?, ?) ON CONFLICT ("p_id") DO UPDATE SET "qty" = excluded.qty WHERE "products"."qty" < excluded.qty',
             (1, 5, 2, 10), id="multi_row_insert_on_conflict_do_update_where"),
        ]
    )
    def test_insert_with_values_source_combinations(self, dummy_dialect: DummyDialect,
                                                     into_param, columns_param, returning_param,
                                                     on_conflict_param, num_rows,
                                                     expected_sql, expected_params):
        # Helper function to recursively set dialect for BaseExpression objects.
        # This is needed because test parameters might initialize expressions with None dialect,
        # and we need to propagate the dummy_dialect before to_sql() is called.
        def set_dialect_recursive(expr, dialect):
            from rhosocial.activerecord.backend.expression import bases, core # Import needed classes
            
            # Only process BaseExpression instances
            if not isinstance(expr, bases.BaseExpression):
                return

            expr._dialect = dialect

            # Recursively set dialect for nested expressions.
            # This covers common patterns in BaseExpression subclasses.
            if hasattr(expr, 'args') and isinstance(expr.args, list):
                for arg in expr.args:
                    set_dialect_recursive(arg, dialect)
            if hasattr(expr, 'elements') and isinstance(expr.elements, list):
                for elem in expr.elements:
                    set_dialect_recursive(elem, dialect)
            if hasattr(expr, 'left'):
                set_dialect_recursive(expr.left, dialect)
            if hasattr(expr, 'right'):
                set_dialect_recursive(expr.right, dialect)
            if hasattr(expr, 'expr'): # For predicates
                set_dialect_recursive(expr.expr, dialect)
            if hasattr(expr, 'value') and isinstance(expr.value, bases.BaseExpression): # For Literal, if value is an expression
                set_dialect_recursive(expr.value, dialect)
            if hasattr(expr, 'subquery'): # For Exists, Subquery
                set_dialect_recursive(expr.subquery, dialect)
            # Specific for OnConflictClause's update_assignments and update_where
            if hasattr(expr, 'update_assignments') and isinstance(expr.update_assignments, dict):
                for k, v in expr.update_assignments.items():
                    set_dialect_recursive(v, dialect)
            if hasattr(expr, 'update_where'):
                set_dialect_recursive(expr.update_where, dialect)
            if hasattr(expr, 'conflict_target') and isinstance(expr.conflict_target, list):
                for target in expr.conflict_target:
                    if isinstance(target, bases.BaseExpression):
                        set_dialect_recursive(target, dialect)


        # --- Prepare dynamic parameters with dummy_dialect ---
        # into parameter
        if isinstance(into_param, TableExpression):
            into_param._dialect = dummy_dialect
        
        # columns for VALUES source
        values_data = []
        if num_rows == 1:
            if columns_param == ["name", "email"]: values_data = [["John Doe", "john@example.com"]]
            elif columns_param == ["product_name"]: values_data = [["Laptop"]]
            elif columns_param == ["amount"]: values_data = [[100.50]]
            elif columns_param == ["item_id"]: values_data = [[10]]
            elif columns_param == ["key", "value"]: values_data = [["cpu_usage", 85.5]]
            elif columns_param is None: values_data = [["event_data"]] # For columns=None case
        elif num_rows == 2:
            if columns_param == ["name", "email"]: values_data = [["Jane Doe", "jane@example.com"], ["Peter Pan", "peter@example.com"]]
            elif columns_param == ["txn_id", "status"]: values_data = [["TXN001", "success"], ["TXN002", "pending"]]
            elif columns_param == ["p_id", "qty"]: values_data = [[1, 5], [2, 10]]

        values_list_expr = []
        for row in values_data:
            values_list_expr.append([Literal(dummy_dialect, val) for val in row])
        source = ValuesSource(dummy_dialect, values_list=values_list_expr)

        # returning parameter
        returning_expr = None
        if returning_param:
            returning_expr = []
            for item in returning_param:
                set_dialect_recursive(item, dummy_dialect) # Apply recursively to returning items
                returning_expr.append(item)

        # on_conflict parameter
        on_conflict_expr = None
        if on_conflict_param:
            set_dialect_recursive(on_conflict_param, dummy_dialect) # Apply recursively to the entire OnConflictClause object
            on_conflict_expr = on_conflict_param # Assign the updated object

        insert_expr = InsertExpression(
            dummy_dialect,
            into=into_param,
            columns=columns_param,
            source=source,
            on_conflict=on_conflict_expr,
            returning=returning_expr
        )
        sql, params = insert_expr.to_sql()

        # --- Assertions ---
        # Basic check for table and columns
        if isinstance(into_param, TableExpression):
            assert f'INSERT INTO "{into_param.name}"' in sql
            if into_param.alias: assert f'AS "{into_param.alias}"' in sql
        else:
            assert f'INSERT INTO "{into_param}"' in sql
        
        # Reintroduce precise checks for column definitions, using regular expressions for robustness.
        import re

        # Get the table name representation in SQL
        if isinstance(into_param, TableExpression):
            # If into_param is a TableExpression, call its to_sql() method to get the string representation.
            table_sql_part = into_param.to_sql()[0]
        else:
            # If into_param is a string, format it as an identifier.
            table_sql_part = dummy_dialect.format_identifier(into_param)
        
        table_name_pattern_escaped = re.escape(table_sql_part)

        if columns_param:
            # Construct the correct column string (with parentheses)
            formatted_cols = [dummy_dialect.format_identifier(c) for c in columns_param]
            expected_column_str_with_parens = f"({', '.join(formatted_cols)})"
            column_names_pattern_escaped = re.escape(expected_column_str_with_parens)
            
            # Find the 'INSERT INTO <table_name> (<column_list>)' pattern
            match_pattern = rf'INSERT INTO\s+{table_name_pattern_escaped}\s+{column_names_pattern_escaped}'
            assert re.search(match_pattern, sql) is not None, \
                   f"Column definition '{expected_column_str_with_parens}' not found or incorrectly placed after table '{table_sql_part}' in SQL: {sql}"
        else: # columns_param is None
            # Find the 'INSERT INTO <table_name> DEFAULT VALUES' or 'INSERT INTO <table_name> VALUES' pattern
            match_pattern_default_values = rf'INSERT INTO\s+{table_name_pattern_escaped}\s+DEFAULT VALUES'
            match_pattern_values = rf'INSERT INTO\s+{table_name_pattern_escaped}\s+VALUES'
            
            assert (re.search(match_pattern_default_values, sql) is not None or
                    re.search(match_pattern_values, sql) is not None), \
                    f"Expected 'DEFAULT VALUES' or 'VALUES' after table '{table_sql_part}' in SQL: {sql}"

        # Check for returning clause
        if returning_param:
            assert 'RETURNING' in sql
        else:
            assert 'RETURNING' not in sql

        # Check for on_conflict clause
        if on_conflict_param:
            assert 'ON CONFLICT' in sql
            if on_conflict_param.do_nothing:
                assert 'DO NOTHING' in sql
            elif on_conflict_param.update_assignments:
                assert 'DO UPDATE SET' in sql
        else:
            assert 'ON CONFLICT' not in sql

        # Exact match for SQL and parameters (this can be complex due to dialect formatting)
        # For simplicity, we directly assert the expected SQL string and parameters
        assert sql == expected_sql
        assert params == expected_params

    # The following tests are replaced by the parameterized test above
    # def test_insert_with_values_source(self, dummy_dialect: DummyDialect): ...
    # def test_multi_row_insert_with_values_source(self, dummy_dialect: DummyDialect): ...

    def test_insert_with_select_source(self, dummy_dialect: DummyDialect):
        """Tests INSERT ... SELECT ... using SelectSource."""
        select_query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "name"), Column(dummy_dialect, "email")],
            from_=TableExpression(dummy_dialect, "old_users"),
            where=Column(dummy_dialect, "status") == Literal(dummy_dialect, "active")
        )
        source = SelectSource(dummy_dialect, select_query=select_query)
        insert_expr = InsertExpression(
            dummy_dialect,
            into="new_users",
            columns=["name", "email"],
            source=source
        )
        sql, params = insert_expr.to_sql()
        expected_select = 'SELECT "name", "email" FROM "old_users" WHERE "status" = ?'
        assert sql == f'INSERT INTO "new_users" ("name", "email") {expected_select}'
        assert params == ("active",)

    def test_insert_with_default_values_source(self, dummy_dialect: DummyDialect):
        """Tests INSERT ... DEFAULT VALUES using DefaultValuesSource."""
        source = DefaultValuesSource(dummy_dialect)
        insert_expr = InsertExpression(
            dummy_dialect,
            into="settings",
            source=source
        )
        sql, params = insert_expr.to_sql()
        assert sql == 'INSERT INTO "settings"  DEFAULT VALUES'
        assert params == ()

    def test_insert_with_returning_clause(self, dummy_dialect: DummyDialect):
        """Tests an INSERT statement with a RETURNING clause."""
        source = ValuesSource(dummy_dialect, values_list=[[Literal(dummy_dialect, "test")]])
        insert_expr = InsertExpression(
            dummy_dialect,
            into="users",
            columns=["name"],
            source=source,
            returning=[Column(dummy_dialect, "id"), RawSQLExpression(dummy_dialect, "created_at")]
        )
        sql, params = insert_expr.to_sql()
        assert sql == 'INSERT INTO "users" ("name") VALUES (?) RETURNING "id", created_at'
        assert params == ("test",)

    def test_insert_on_conflict_do_nothing(self, dummy_dialect: DummyDialect):
        """Tests ON CONFLICT DO NOTHING for upsert."""
        source = ValuesSource(dummy_dialect, values_list=[[Literal(dummy_dialect, 1), Literal(dummy_dialect, "test")]])
        on_conflict = OnConflictClause(
            dummy_dialect,
            conflict_target=["id"],
            do_nothing=True
        )
        insert_expr = InsertExpression(
            dummy_dialect,
            into="products",
            columns=["id", "name"],
            source=source,
            on_conflict=on_conflict
        )
        sql, params = insert_expr.to_sql()
        assert sql == 'INSERT INTO "products" ("id", "name") VALUES (?, ?) ON CONFLICT ("id") DO NOTHING'
        assert params == (1, "test")

    def test_insert_on_conflict_do_update(self, dummy_dialect: DummyDialect):
        """Tests ON CONFLICT DO UPDATE for upsert."""
        source = ValuesSource(dummy_dialect, values_list=[
            [Literal(dummy_dialect, 1), Literal(dummy_dialect, "Updated Name")]
        ])
        on_conflict = OnConflictClause(
            dummy_dialect,
            conflict_target=[Column(dummy_dialect, "id")],
            update_assignments={
                "name": Column(dummy_dialect, "name", "excluded"),
                "updated_at": RawSQLExpression(dummy_dialect, "CURRENT_TIMESTAMP")
            }
        )
        insert_expr = InsertExpression(
            dummy_dialect,
            into="products",
            columns=["id", "name"],
            source=source,
            on_conflict=on_conflict
        )
        sql, params = insert_expr.to_sql()
        expected_sql = ('INSERT INTO "products" ("id", "name") VALUES (?, ?) '
                        'ON CONFLICT ("id") DO UPDATE SET "name" = "excluded"."name", '
                        '"updated_at" = CURRENT_TIMESTAMP')
        assert sql == expected_sql
        assert params == (1, "Updated Name")

    def test_insert_on_conflict_do_update_with_where(self, dummy_dialect: DummyDialect):
        """Tests ON CONFLICT DO UPDATE with a WHERE condition."""
        source = ValuesSource(dummy_dialect, values_list=[
            [Literal(dummy_dialect, 1), Literal(dummy_dialect, "Updated Name")]
        ])
        on_conflict = OnConflictClause(
            dummy_dialect,
            conflict_target=["id"],
            update_assignments={"name": Column(dummy_dialect, "name", "excluded")},
            update_where=Column(dummy_dialect, "is_active", "products") == Literal(dummy_dialect, True)
        )
        insert_expr = InsertExpression(
            dummy_dialect,
            into="products",
            columns=["id", "name"],
            source=source,
            on_conflict=on_conflict
        )
        sql, params = insert_expr.to_sql()
        expected_sql = ('INSERT INTO "products" ("id", "name") VALUES (?, ?) '
                        'ON CONFLICT ("id") DO UPDATE SET "name" = "excluded"."name" '
                        'WHERE "products"."is_active" = ?')
        assert sql == expected_sql
        assert params == (1, "Updated Name", True)

    def test_insert_validation_error_default_values_with_cols(self, dummy_dialect: DummyDialect):
        """Tests validation for using DefaultValuesSource with columns."""
        with pytest.raises(ValueError, match="'DEFAULT VALUES' source cannot be used with 'columns'."):
            InsertExpression(
                dummy_dialect,
                into="settings",
                source=DefaultValuesSource(dummy_dialect),
                columns=["id"]
            )
            
    def test_insert_validation_error_on_conflict_with_invalid_source(self, dummy_dialect: DummyDialect):
        """Tests that 'on_conflict' raises an error with an unsupported source like DefaultValuesSource."""
        with pytest.raises(ValueError, match="'on_conflict' is only supported for 'VALUES' or 'SELECT' sources."):
            InsertExpression(
                dummy_dialect,
                into="settings",
                source=DefaultValuesSource(dummy_dialect),
                on_conflict=OnConflictClause(dummy_dialect, conflict_target=["id"], do_nothing=True)
            )

    def test_insert_with_table_expression(self, dummy_dialect: DummyDialect):
        """Tests that 'into' can be a TableExpression."""
        source = ValuesSource(dummy_dialect, values_list=[[Literal(dummy_dialect, "test")]])
        insert_expr = InsertExpression(
            dummy_dialect,
            into=TableExpression(dummy_dialect, "users", alias="u"),
            columns=["name"],
            source=source
        )
        sql, params = insert_expr.to_sql()
        assert sql == 'INSERT INTO "users" AS "u" ("name") VALUES (?)'
        assert params == ("test",)