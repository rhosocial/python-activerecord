# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_composite_pk.py
from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
    TableConstraint,
    TableConstraintType,
    ComparisonPredicate,
    Literal,
)
from rhosocial.activerecord.backend.expression.core import Column, TableExpression
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType

dialect = DummyDialect()


class TestCompositePKDDL:
    def test_create_table_dual_pk(self):
        expr = CreateTableExpression(
            dialect=dialect,
            table="order_items",
            columns=[
                ColumnDefinition("order_id", IntegerType(),
                    constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
                ColumnDefinition("product_id", IntegerType(),
                    constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ],
            table_constraints=[
                TableConstraint(
                    constraint_type=TableConstraintType.PRIMARY_KEY,
                    columns=["order_id", "product_id"],
                ),
            ],
        )
        sql, params = expr.to_sql()
        assert "PRIMARY KEY (\"order_id\", \"product_id\")" in sql

    def test_create_table_triple_pk(self):
        expr = CreateTableExpression(
            dialect=dialect,
            table="store_inventory",
            columns=[
                ColumnDefinition("store_id", IntegerType(),
                    constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
                ColumnDefinition("product_id", IntegerType(),
                    constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
                ColumnDefinition("batch_id", VarCharType(length=64),
                    constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ],
            table_constraints=[
                TableConstraint(
                    constraint_type=TableConstraintType.PRIMARY_KEY,
                    columns=["store_id", "product_id", "batch_id"],
                ),
            ],
        )
        sql, params = expr.to_sql()
        assert "PRIMARY KEY" in sql
        assert "store_id" in sql
        assert "product_id" in sql
        assert "batch_id" in sql

    def test_pk_columns_not_null(self):
        expr = CreateTableExpression(
            dialect=dialect,
            table="t",
            columns=[
                ColumnDefinition("a", IntegerType(),
                    constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
                ColumnDefinition("b", IntegerType(),
                    constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ],
            table_constraints=[
                TableConstraint(
                    constraint_type=TableConstraintType.PRIMARY_KEY,
                    columns=["a", "b"],
                ),
            ],
        )
        sql, params = expr.to_sql()
        assert "NOT NULL" in sql
        assert sql.index("PRIMARY KEY") > sql.index("NOT NULL")


class TestCompositePKPredicate:
    def test_composite_pk_where_predicate(self):
        pred = ComparisonPredicate(
            dialect, "=", Column(dialect, "order_id"), Literal(dialect, 1)
        ) & ComparisonPredicate(
            dialect, "=", Column(dialect, "product_id"), Literal(dialect, 101)
        )
        sql, params = pred.to_sql()
        assert "order_id" in sql
        assert "product_id" in sql
        assert "=" in sql
        assert len(sql.split("AND")) == 2 or sql.count("=") == 2

    def test_composite_pk_chain_or_predicate(self):
        pred1 = ComparisonPredicate(
            dialect, "=", Column(dialect, "order_id"), Literal(dialect, 1)
        ) & ComparisonPredicate(
            dialect, "=", Column(dialect, "product_id"), Literal(dialect, 101)
        )
        pred2 = ComparisonPredicate(
            dialect, "=", Column(dialect, "order_id"), Literal(dialect, 2)
        ) & ComparisonPredicate(
            dialect, "=", Column(dialect, "product_id"), Literal(dialect, 101)
        )
        combined = pred1 | pred2
        sql, params = combined.to_sql()
        assert "OR" in sql.upper()
        assert sql.count("=") >= 4
