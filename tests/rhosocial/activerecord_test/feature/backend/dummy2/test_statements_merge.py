import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, TableExpression, ComparisonPredicate,
    MergeExpression, MergeAction, MergeActionType
)
from rhosocial.activerecord.backend.expression.query_clauses import ValuesExpression
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


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