import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, RawSQLExpression, Subquery, TableExpression,
    ComparisonPredicate, FunctionCall,
    JoinExpression, CTEExpression, GroupingExpression, ValuesExpression,
    MergeExpression, MergeAction, OrderedSetAggregation,
    MergeActionType
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

class TestClauseExpressions:
    """Tests for various SQL clause-related expressions."""

    # --- JoinExpression ---
    @pytest.mark.parametrize("left_table, right_table, join_type, condition, using, expected_sql, expected_params", [
        (TableExpression(None, "users", "u"), TableExpression(None, "orders", "o"), "INNER",
         ComparisonPredicate(None, "=", Column(None, "id", "u"), Column(None, "user_id", "o")), None,
         '"users" AS "u" INNER JOIN "orders" AS "o" ON ("u"."id" = "o"."user_id")', ()),
        (TableExpression(None, "products", "p"), TableExpression(None, "categories", "c"), "LEFT",
         ComparisonPredicate(None, "=", Column(None, "category_id", "p"), Column(None, "id", "c")), None,
         '"products" AS "p" LEFT JOIN "categories" AS "c" ON ("p"."category_id" = "c"."id")', ()),
        (TableExpression(None, "customers"), TableExpression(None, "addresses"), "FULL",
         None, ["customer_id"], '"customers" FULL JOIN "addresses" USING ("customer_id")', ()),
        (TableExpression(None, "tbl1"), TableExpression(None, "tbl2"), "CROSS",
         None, None, '"tbl1" CROSS JOIN "tbl2"', ()),
    ])
    def test_join_expression(self, dummy_dialect: DummyDialect, left_table, right_table, join_type, condition, using, expected_sql, expected_params):
        """Tests various types of JOIN expressions."""
        # Assign dialect to sub-expressions if they exist
        left_table.dialect = dummy_dialect
        right_table.dialect = dummy_dialect
        if condition:
            condition.dialect = dummy_dialect # Condition handles its own sub-expressions
        
        join_expr = JoinExpression(dummy_dialect, left_table, right_table, join_type, condition=condition, using=using)
        sql, params = join_expr.to_sql()
        assert sql == expected_sql
        assert params == expected_params

    # --- CTEExpression ---
    def test_basic_cte_expression(self, dummy_dialect: DummyDialect):
        """Tests a basic Common Table Expression (CTE)."""
        cte_query = Subquery(dummy_dialect, "SELECT id, name FROM employees WHERE salary > ?", (50000,))
        cte_expr = CTEExpression(dummy_dialect, name="high_earners", query=cte_query, columns=["id", "name"])
        sql, params = cte_expr.to_sql()
        assert sql == '"high_earners" ("id", "name") AS (SELECT id, name FROM employees WHERE salary > ?)'
        assert params == (50000,)

    def test_recursive_cte_expression(self, dummy_dialect: DummyDialect):
        """Tests a recursive CTE."""
        cte_query_sql = """
            SELECT id, name, manager_id, 1 AS level
            FROM employees
            WHERE manager_id IS NULL
            UNION ALL
            SELECT e.id, e.name, e.manager_id, t.level + 1
            FROM employees e INNER JOIN org_tree t ON e.manager_id = t.id
        """
        cte_query = RawSQLExpression(dummy_dialect, cte_query_sql) # Or Subquery
        cte_expr = CTEExpression(dummy_dialect, name="org_tree", query=cte_query, recursive=True)
        sql, params = cte_expr.to_sql()
        assert sql == f'RECURSIVE "org_tree" AS ({cte_query_sql.strip()})'
        assert params == ()

    def test_materialized_cte_expression(self, dummy_dialect: DummyDialect):
        """Tests a materialized CTE."""
        cte_query = Subquery(dummy_dialect, "SELECT * FROM large_data WHERE condition = ?", (True,))
        cte_expr = CTEExpression(dummy_dialect, name="cached_data", query=cte_query, materialized=True)
        sql, params = cte_expr.to_sql()
        assert sql == '"cached_data" AS MATERIALIZED (SELECT * FROM large_data WHERE condition = ?)'
        assert params == (True,)

    # --- GroupingExpression (ROLLUP, CUBE, GROUPING SETS) ---
    @pytest.mark.parametrize("grouping_type, args, expected_sql", [
        ("ROLLUP", [Column(None, "year"), Column(None, "quarter")], 'ROLLUP("year", "quarter")'),
        ("CUBE", [Column(None, "region"), Column(None, "product")], 'CUBE("region", "product")'),
        ("GROUPING SETS", [[Column(None, "country")], [Column(None, "city")]], 'GROUPING SETS(("country"), ("city"))'),
    ])
    def test_grouping_expression(self, dummy_dialect: DummyDialect, grouping_type, args, expected_sql):
        """Tests advanced GROUP BY features: ROLLUP, CUBE, GROUPING SETS."""
        # Assign dialect to arguments
        processed_args = []
        if grouping_type == "GROUPING SETS":
            for group_set in args:
                processed_group_set = []
                for arg in group_set:
                    arg.dialect = dummy_dialect
                    processed_group_set.append(arg)
                processed_args.append(processed_group_set)
        else:
            for arg in args:
                arg.dialect = dummy_dialect
                processed_args.append(arg)

        grouping_expr = GroupingExpression(dummy_dialect, grouping_type, processed_args)
        sql, params = grouping_expr.to_sql()
        assert sql == expected_sql
        assert params == ()

    # --- ValuesExpression ---
    @pytest.mark.parametrize("values_data, alias, columns, expected_sql, expected_params", [
        ([(1, "A"), (2, "B")], "t", ["id", "val"], '(VALUES (?, ?), (?, ?)) AS "t"("id", "val")', (1, "A", 2, "B")),
        ([("item1",)], "items", ["name"], '(VALUES (?)) AS "items"("name")', ("item1",)),
    ])
    def test_values_expression(self, dummy_dialect: DummyDialect, values_data, alias, columns, expected_sql, expected_params):
        """Tests VALUES expressions to generate inline tables."""
        values_expr = ValuesExpression(dummy_dialect, values_data, alias, columns)
        sql, params = values_expr.to_sql()
        assert sql == expected_sql
        assert params == expected_params

    # --- MergeExpression ---
    def test_merge_expression_basic(self, dummy_dialect: DummyDialect):
        """Tests a basic MERGE statement with WHEN MATCHED UPDATE and WHEN NOT MATCHED INSERT."""
        target_table = TableExpression(dummy_dialect, "products", "p")
        source_values = ValuesExpression(dummy_dialect, [(1, "New Product A", 15.0)], "new_prods", ["id", "name", "price"])
        on_condition = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "id", "p"), Column(dummy_dialect, "id", "new_prods"))

        when_matched_update = MergeAction(
            action_type=MergeActionType.UPDATE,
            assignments={
                "name": Column(dummy_dialect, "name", "new_prods"),
                "price": Column(dummy_dialect, "price", "new_prods")
            }
        )
        when_not_matched_insert = MergeAction(
            action_type=MergeActionType.INSERT,
            assignments={ # DummyDialect expects assignments to carry column names for INSERT
                "id": Column(dummy_dialect, "id", "new_prods"),
                "name": Column(dummy_dialect, "name", "new_prods"),
                "price": Column(dummy_dialect, "price", "new_prods")
            }
        )

        merge_expr = MergeExpression(
            dummy_dialect,
            target_table=target_table,
            source=source_values,
            on_condition=on_condition,
            when_matched=[when_matched_update],
            when_not_matched=[when_not_matched_insert]
        )
        sql, params = merge_expr.to_sql()
        expected_sql = ('MERGE INTO "products" AS "p" USING (VALUES (?, ?, ?)) AS "new_prods"("id", "name", "price") ON ("p"."id" = "new_prods"."id") '
                        'WHEN MATCHED THEN UPDATE SET name = "new_prods"."name", price = "new_prods"."price" '
                        'WHEN NOT MATCHED THEN INSERT ("id", "name", "price") VALUES ("new_prods"."id", "new_prods"."name", "new_prods"."price")')
        assert sql == expected_sql
        assert params == (1, "New Product A", 15.0, 1, "New Product A", 15.0) # Parameters are duplicated for dummy dialect

    # --- OrderedSetAggregation ---
    def test_ordered_set_aggregation_percentile_cont(self, dummy_dialect: DummyDialect):
        """Tests PERCENTILE_CONT WITHIN GROUP ordered-set aggregate function."""
        expr = OrderedSetAggregation(
            dummy_dialect,
            "PERCENTILE_CONT",
            args=[Literal(dummy_dialect, 0.5)],
            order_by=[Column(dummy_dialect, "salary")],
            alias="median_salary"
        )
        sql, params = expr.to_sql()
        expected_sql = 'PERCENTILE_CONT(?) WITHIN GROUP (ORDER BY "salary") AS "median_salary"'
        assert sql == expected_sql
        assert params == (0.5,)

    def test_ordered_set_aggregation_listagg(self, dummy_dialect: DummyDialect):
        """Tests LISTAGG WITHIN GROUP ordered-set aggregate function."""
        expr = OrderedSetAggregation(
            dummy_dialect,
            "LISTAGG",
            args=[Column(dummy_dialect, "name"), Literal(dummy_dialect, ",")],
            order_by=[Column(dummy_dialect, "name")],
            alias="employee_list"
        )
        sql, params = expr.to_sql()
        expected_sql = 'LISTAGG("name", ?) WITHIN GROUP (ORDER BY "name") AS "employee_list"'
        assert sql == expected_sql
        assert params == (",",)
