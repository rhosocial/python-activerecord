# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_merge.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, TableExpression, ComparisonPredicate,
    MergeExpression, MergeAction, MergeActionType
)
from rhosocial.activerecord.backend.expression.query_clauses import ValuesExpression
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestMergeStatements:
    """Tests for MERGE statements with various WHEN clause combinations."""

    def test_merge_expression_basic(self, dummy_dialect: DummyDialect):
        """Tests a basic MERGE statement with WHEN MATCHED UPDATE and WHEN NOT MATCHED INSERT."""
        from rhosocial.activerecord.backend.expression import ValuesExpression

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

    def test_merge_with_update_action(self, dummy_dialect: DummyDialect):
        """Tests MERGE with UPDATE action in WHEN MATCHED clause."""
        from rhosocial.activerecord.backend.expression import ValuesExpression

        target_table = TableExpression(dummy_dialect, "products", "p")
        source_values = ValuesExpression(dummy_dialect, [(1, "Updated Product", 25.0)], "new_prods", ["id", "name", "price"])
        on_condition = ComparisonPredicate(dummy_dialect, "=",
                                         Column(dummy_dialect, "id", "p"),
                                         Column(dummy_dialect, "id", "new_prods"))

        # WHEN MATCHED: UPDATE action
        when_matched_update = MergeAction(
            action_type=MergeActionType.UPDATE,
            assignments={
                "name": Column(dummy_dialect, "name", "new_prods"),
                "price": Column(dummy_dialect, "price", "new_prods")
            }
        )

        merge_expr = MergeExpression(
            dummy_dialect,
            target_table=target_table,
            source=source_values,
            on_condition=on_condition,
            when_matched=[when_matched_update]
        )
        sql, params = merge_expr.to_sql()
        assert "WHEN MATCHED THEN UPDATE" in sql
        assert 'SET "name" = ' in sql  # Column names are now properly quoted
        assert params == (1, "Updated Product", 25.0)  # Only the original values, no duplication

    def test_merge_with_insert_action(self, dummy_dialect: DummyDialect):
        """Tests MERGE with INSERT action in WHEN NOT MATCHED clause."""
        from rhosocial.activerecord.backend.expression import ValuesExpression

        target_table = TableExpression(dummy_dialect, "products", "p")
        source_values = ValuesExpression(dummy_dialect, [(2, "New Product B", 35.0)], "new_prods", ["id", "name", "price"])
        on_condition = ComparisonPredicate(dummy_dialect, "=",
                                         Column(dummy_dialect, "id", "p"),
                                         Column(dummy_dialect, "id", "new_prods"))

        # WHEN NOT MATCHED: INSERT action
        when_not_matched_insert = MergeAction(
            action_type=MergeActionType.INSERT,
            assignments={
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
            when_not_matched=[when_not_matched_insert]
        )
        sql, params = merge_expr.to_sql()
        assert "WHEN NOT MATCHED THEN INSERT" in sql
        assert "VALUES (" in sql
        assert params == (2, "New Product B", 35.0)  # Only the original values, no duplication

    def test_merge_with_delete_action(self, dummy_dialect: DummyDialect):
        """Tests MERGE with DELETE action in WHEN MATCHED clause."""
        from rhosocial.activerecord.backend.expression import ValuesExpression

        target_table = TableExpression(dummy_dialect, "orders", "ord")
        source_values = ValuesExpression(dummy_dialect, [(555,)], "cancel_orders", ["order_id"])
        on_condition = ComparisonPredicate(dummy_dialect, "=",
                                         Column(dummy_dialect, "order_id", "ord"),
                                         Column(dummy_dialect, "order_id", "cancel_orders"))

        # WHEN MATCHED: DELETE action (only for pending orders)
        when_matched_delete = MergeAction(
            action_type=MergeActionType.DELETE,
            condition=ComparisonPredicate(dummy_dialect, "=",
                                        Column(dummy_dialect, "status", "ord"),
                                        Literal(dummy_dialect, "pending"))
        )

        merge_expr = MergeExpression(
            dummy_dialect,
            target_table=target_table,
            source=source_values,
            on_condition=on_condition,
            when_matched=[when_matched_delete]
        )
        sql, params = merge_expr.to_sql()

        assert "WHEN MATCHED" in sql
        assert "DELETE" in sql
        # Parameters include source value (555) and condition value ("pending")
        assert 555 in params
        assert "pending" in params

    def test_merge_with_conditions(self, dummy_dialect: DummyDialect):
        """Tests MERGE with conditions in WHEN clauses."""
        from rhosocial.activerecord.backend.expression import ValuesExpression

        target_table = TableExpression(dummy_dialect, "employees", "emp")
        source_values = ValuesExpression(dummy_dialect, [(101, "John Doe", 60000)], "new_emps", ["id", "name", "salary"])
        on_condition = ComparisonPredicate(dummy_dialect, "=",
                                         Column(dummy_dialect, "id", "emp"),
                                         Column(dummy_dialect, "id", "new_emps"))

        # WHEN MATCHED condition: only update if salary is higher
        when_matched = MergeAction(
            action_type=MergeActionType.UPDATE,
            assignments={
                "name": Column(dummy_dialect, "name", "new_emps"),
                "salary": Column(dummy_dialect, "salary", "new_emps")
            },
            condition=ComparisonPredicate(dummy_dialect, ">",
                                        Column(dummy_dialect, "salary", "new_emps"),
                                        Column(dummy_dialect, "salary", "emp"))
        )

        # WHEN NOT MATCHED condition: only insert if salary >= 50000
        when_not_matched = MergeAction(
            action_type=MergeActionType.INSERT,
            assignments={
                "id": Column(dummy_dialect, "id", "new_emps"),
                "name": Column(dummy_dialect, "name", "new_emps"),
                "salary": Column(dummy_dialect, "salary", "new_emps")
            },
            condition=ComparisonPredicate(dummy_dialect, ">=",
                                        Column(dummy_dialect, "salary", "new_emps"),
                                        Literal(dummy_dialect, 50000))
        )

        merge_expr = MergeExpression(
            dummy_dialect,
            target_table=target_table,
            source=source_values,
            on_condition=on_condition,
            when_matched=[when_matched],
            when_not_matched=[when_not_matched]
        )
        sql, params = merge_expr.to_sql()

        # Validate that conditions appear in the SQL
        assert "WHEN MATCHED AND" in sql
        assert "WHEN NOT MATCHED AND" in sql
        # Check that the parameters contain all expected values (source values plus condition values)
        assert len(params) == 4  # 3 source values + 1 condition value (50000)
        # Verify the presence of key values
        assert 101 in params  # source id
        assert "John Doe" in params  # source name
        assert 60000 in params  # source salary and condition value
        assert 50000 in params  # condition value

    def test_merge_delete_action(self, dummy_dialect: DummyDialect):
        """Tests MERGE with DELETE action in WHEN MATCHED clause."""
        from rhosocial.activerecord.backend.expression import ValuesExpression

        target_table = TableExpression(dummy_dialect, "orders", "ord")
        source_cancel = ValuesExpression(dummy_dialect, [(555,)], "cancel_orders", ["order_id"])
        on_condition = ComparisonPredicate(dummy_dialect, "=",
                                         Column(dummy_dialect, "order_id", "ord"),
                                         Column(dummy_dialect, "order_id", "cancel_orders"))

        # WHEN MATCHED: delete pending orders only
        when_matched_delete = MergeAction(
            action_type=MergeActionType.DELETE,
            condition=ComparisonPredicate(dummy_dialect, "=",
                                        Column(dummy_dialect, "status", "ord"),
                                        Literal(dummy_dialect, "pending"))
        )

        merge_expr = MergeExpression(
            dummy_dialect,
            target_table=target_table,
            source=source_cancel,
            on_condition=on_condition,
            when_matched=[when_matched_delete]
        )
        sql, params = merge_expr.to_sql()

        assert "WHEN MATCHED" in sql
        assert "DELETE" in sql
        # The parameters are 555 (from source) and "pending" (from condition)
        assert len(params) == 2  # source value (555) and condition value ("pending") appear once each
        assert 555 in params
        assert "pending" in params


class TestMergeNotMatchedBySource:
    """Tests for WHEN NOT MATCHED BY SOURCE clause functionality."""

    def test_merge_with_not_matched_by_source_delete(self, dummy_dialect: DummyDialect):
        """Tests MERGE with WHEN NOT MATCHED BY SOURCE DELETE action."""
        target_table = TableExpression(dummy_dialect, "existing_products", "ep")
        source_values = ValuesExpression(
            dummy_dialect,
            values=[(Literal(dummy_dialect, 1), Literal(dummy_dialect, "Product A")), (Literal(dummy_dialect, 2), Literal(dummy_dialect, "Product B"))],
            alias="new_prods",
            column_names=["id", "name"]
        )
        on_condition = ComparisonPredicate(
            dummy_dialect,
            "=",
            Column(dummy_dialect, "id", "ep"),
            Column(dummy_dialect, "id", "new_prods")
        )

        # WHEN MATCHED: UPDATE
        when_matched_update = MergeAction(
            action_type=MergeActionType.UPDATE,
            assignments={
                "name": Column(dummy_dialect, "name", "new_prods")
            }
        )

        # WHEN NOT MATCHED: INSERT
        when_not_matched_insert = MergeAction(
            action_type=MergeActionType.INSERT,
            assignments={
                "id": Column(dummy_dialect, "id", "new_prods"),
                "name": Column(dummy_dialect, "name", "new_prods")
            }
        )

        # WHEN NOT MATCHED BY SOURCE: DELETE (remove unmatched records from target)
        when_not_matched_by_source_delete = MergeAction(
            action_type=MergeActionType.DELETE
        )

        merge_expr = MergeExpression(
            dummy_dialect,
            target_table=target_table,
            source=source_values,
            on_condition=on_condition,
            when_matched=[when_matched_update],
            when_not_matched=[when_not_matched_insert],
            when_not_matched_by_source=[when_not_matched_by_source_delete]
        )

        sql, params = merge_expr.to_sql()

        # Verify that the SQL contains the NOT MATCHED BY SOURCE clause
        assert "WHEN NOT MATCHED BY SOURCE THEN DELETE" in sql
        assert 'MERGE INTO "existing_products" AS "ep" USING (VALUES (?, ?), (?, ?)) AS "new_prods"("id", "name") ON "ep"."id" = "new_prods"."id"' in sql
        assert params == (1, "Product A", 2, "Product B")

    def test_merge_with_not_matched_by_source_update(self, dummy_dialect: DummyDialect):
        """Tests MERGE with WHEN NOT MATCHED BY SOURCE UPDATE action."""
        target_table = TableExpression(dummy_dialect, "customers", "c")
        source_values = ValuesExpression(
            dummy_dialect,
            values=[(Literal(dummy_dialect, 1), Literal(dummy_dialect, "Active")), (Literal(dummy_dialect, 2), Literal(dummy_dialect, "Active"))],
            alias="updated_cust",
            column_names=["id", "status"]
        )
        on_condition = ComparisonPredicate(
            dummy_dialect,
            "=",
            Column(dummy_dialect, "id", "c"),
            Column(dummy_dialect, "id", "updated_cust")
        )

        # WHEN NOT MATCHED BY SOURCE: UPDATE (mark unmatched records as inactive)
        when_not_matched_by_source_update = MergeAction(
            action_type=MergeActionType.UPDATE,
            assignments={
                "status": Literal(dummy_dialect, "inactive")
            }
        )

        merge_expr = MergeExpression(
            dummy_dialect,
            target_table=target_table,
            source=source_values,
            on_condition=on_condition,
            when_not_matched_by_source=[when_not_matched_by_source_update]
        )

        sql, params = merge_expr.to_sql()

        # Verify that the SQL contains the NOT MATCHED BY SOURCE UPDATE clause
        assert "WHEN NOT MATCHED BY SOURCE THEN UPDATE SET" in sql
        assert '"status" = ?' in sql
        # Check that "inactive" parameter is in params
        assert "inactive" in params

    def test_merge_with_not_matched_by_source_and_condition(self, dummy_dialect: DummyDialect):
        """Tests MERGE with WHEN NOT MATCHED BY SOURCE and additional condition."""
        target_table = TableExpression(dummy_dialect, "inventory", "inv")
        source_values = ValuesExpression(
            dummy_dialect,
            values=[(Literal(dummy_dialect, 1), Literal(dummy_dialect, "Widget A"), Literal(dummy_dialect, 10)), (Literal(dummy_dialect, 2), Literal(dummy_dialect, "Widget B"), Literal(dummy_dialect, 5))],
            alias="new_inv",
            column_names=["product_id", "name", "quantity"]
        )
        on_condition = ComparisonPredicate(
            dummy_dialect,
            "=",
            Column(dummy_dialect, "product_id", "inv"),
            Column(dummy_dialect, "product_id", "new_inv")
        )

        # WHEN NOT MATCHED BY SOURCE: DELETE with condition (only remove if quantity > threshold)
        when_not_matched_by_source_delete = MergeAction(
            action_type=MergeActionType.DELETE,
            condition=ComparisonPredicate(
                dummy_dialect,
                ">",
                Column(dummy_dialect, "quantity", "inv"),
                Literal(dummy_dialect, 100)
            )
        )

        merge_expr = MergeExpression(
            dummy_dialect,
            target_table=target_table,
            source=source_values,
            on_condition=on_condition,
            when_not_matched_by_source=[when_not_matched_by_source_delete]
        )

        sql, params = merge_expr.to_sql()

        # Verify that the SQL contains the NOT MATCHED BY SOURCE clause with AND condition
        assert "WHEN NOT MATCHED BY SOURCE AND" in sql
        assert "THEN DELETE" in sql
        # Check that 100 parameter is in params
        assert 100 in params