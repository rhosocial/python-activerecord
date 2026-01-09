# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_expressions_clauses.py
import pytest

from rhosocial.activerecord.backend.expression import (
    Column, Literal, RawSQLExpression, Subquery, TableExpression,
    ComparisonPredicate, JoinExpression, CTEExpression, GroupingExpression, ValuesExpression,
    MergeExpression, MergeAction, OrderedSetAggregation,
    MergeActionType
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestClauseExpressions:
    """Tests for various SQL clause-related expressions."""

    # --- JoinExpression ---
    @pytest.mark.parametrize("left_data, right_data, join_type, condition_data, using, expected_sql, expected_params", [
        (("users", "u"), ("orders", "o"), "INNER JOIN", ("=", ("id", "u"), ("user_id", "o")), None,
         '"users" AS "u" INNER JOIN "orders" AS "o" ON "u"."id" = "o"."user_id"', ()),
        (("products", "p"), ("categories", "c"), "LEFT JOIN", ("=", ("category_id", "p"), ("id", "c")), None,
         '"products" AS "p" LEFT JOIN "categories" AS "c" ON "p"."category_id" = "c"."id"', ()),
        (("customers", None), ("addresses", None), "FULL JOIN", None, ["customer_id"],
         '"customers" FULL JOIN "addresses" USING ("customer_id")', ()),
        (("tbl1", None), ("tbl2", None), "CROSS JOIN", None, None,
         '"tbl1" CROSS JOIN "tbl2"', ()),
    ])
    def test_join_expression(self, dummy_dialect: DummyDialect, left_data, right_data, join_type, condition_data, using, expected_sql, expected_params):
        """Tests various types of JOIN expressions."""
        left_table = TableExpression(dummy_dialect, left_data[0], alias=left_data[1])
        right_table = TableExpression(dummy_dialect, right_data[0], alias=right_data[1])
        
        condition = None
        if condition_data:
            op, left_col, right_col = condition_data
            condition = ComparisonPredicate(dummy_dialect, op, 
                                            Column(dummy_dialect, left_col[0], table=left_col[1]), 
                                            Column(dummy_dialect, right_col[0], table=right_col[1]))
        
        join_expr = JoinExpression(dummy_dialect, left_table, right_table, join_type=join_type, condition=condition, using=using)
        sql, params = join_expr.to_sql()
        assert sql == expected_sql
        assert params == expected_params

    def test_join_expression_validation_both_condition_and_using(self, dummy_dialect: DummyDialect):
        """Test that JoinExpression raises ValueError when both condition and using are provided."""
        left_table = TableExpression(dummy_dialect, "users")
        right_table = TableExpression(dummy_dialect, "profiles")
        condition = ComparisonPredicate(
            dummy_dialect,
            "=",
            Column(dummy_dialect, "id", table="users"),
            Column(dummy_dialect, "user_id", table="profiles")
        )

        with pytest.raises(ValueError, match="Cannot specify both 'condition' \\(ON\\) and 'using' \\(USING\\) clauses in a JOIN"):
            JoinExpression(
                dummy_dialect,
                left_table,
                right_table,
                join_type="INNER",
                condition=condition,
                using=["user_id"]
            )

    # --- CTEExpression ---
    def test_basic_cte_expression(self, dummy_dialect: DummyDialect):
        """Tests a basic Common Table Expression (CTE)."""
        cte_query = Subquery(dummy_dialect, "SELECT id, name FROM employees WHERE salary > ?", (50000,))
        cte_expr = CTEExpression(dummy_dialect, name="high_earners", query=cte_query, columns=["id", "name"])
        sql, params = cte_expr.to_sql()
        assert sql == '"high_earners" ("id", "name") AS ((SELECT id, name FROM employees WHERE salary > ?))'
        assert params == (50000,)

    def test_recursive_cte_expression(self, dummy_dialect: DummyDialect):
        """Tests a recursive CTE."""
        cte_query_sql = """SELECT id, name, manager_id, 1 AS level FROM employees WHERE manager_id IS NULL UNION ALL SELECT e.id, e.name, e.manager_id, t.level + 1 FROM employees e INNER JOIN org_tree t ON e.manager_id = t.id"""
        cte_query = RawSQLExpression(dummy_dialect, cte_query_sql) # Or Subquery
        cte_expr = CTEExpression(dummy_dialect, name="org_tree", query=cte_query)
        sql, params = cte_expr.to_sql()
        # The recursive flag is now handled at the WITH clause level, not individual CTE level
        # So the CTE itself should not have RECURSIVE keyword
        assert sql == f'"org_tree" AS ({cte_query_sql.strip()})'
        assert params == ()

    def test_materialized_cte_expression(self, dummy_dialect: DummyDialect):
        """Tests a materialized CTE."""
        cte_query = Subquery(dummy_dialect, "SELECT * FROM large_data WHERE condition = ?", (True,))
        cte_expr = CTEExpression(dummy_dialect, name="cached_data", query=cte_query, materialized=True)
        sql, params = cte_expr.to_sql()
        assert sql == '"cached_data" AS MATERIALIZED ((SELECT * FROM large_data WHERE condition = ?))'
        assert params == (True,)

    # --- GroupingExpression (ROLLUP, CUBE, GROUPING SETS) ---
    @pytest.mark.parametrize("grouping_type, args_data, expected_sql", [
        ("ROLLUP", [("year",), ("quarter",)], 'ROLLUP("year", "quarter")'),
        ("CUBE", [("region",), ("product",)], 'CUBE("region", "product")'),
        ("GROUPING SETS", [[("country",)], [("city",)]], 'GROUPING SETS(("country"), ("city"))'),
    ])
    def test_grouping_expression(self, dummy_dialect: DummyDialect, grouping_type, args_data, expected_sql):
        """Tests advanced GROUP BY features: ROLLUP, CUBE, GROUPING SETS."""
        # Assign dialect to arguments
        processed_args = []
        if grouping_type == "GROUPING SETS":
            for group_set_data in args_data:
                processed_group_set = []
                for arg_data in group_set_data:
                    processed_group_set.append(Column(dummy_dialect, *arg_data))
                processed_args.append(processed_group_set)
        else:
            for arg_data in args_data:
                processed_args.append(Column(dummy_dialect, *arg_data))

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
        expected_sql = ('MERGE INTO "products" AS "p" USING (VALUES (?, ?, ?)) AS "new_prods"("id", "name", "price") ON "p"."id" = "new_prods"."id" '
                        'WHEN MATCHED THEN UPDATE SET "name" = "new_prods"."name", "price" = "new_prods"."price" '
                        'WHEN NOT MATCHED THEN INSERT ("id", "name", "price") VALUES ("new_prods"."id", "new_prods"."name", "new_prods"."price")')
        assert sql == expected_sql
        assert params == (1, "New Product A", 15.0)  # Only the original values, no duplication

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
