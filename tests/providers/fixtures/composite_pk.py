# tests/providers/fixtures/composite_pk.py
from typing import Callable, Dict

from rhosocial.activerecord.backend.expression.types import DecimalType, IntegerType, TextType, VarCharType
from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    TableExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
    TableConstraint,
    TableConstraintType,
)


def create_order_items_table(dialect, table_name: str = "order_items") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("order_id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("product_id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("quantity", IntegerType(),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=1),
                ]),
            ColumnDefinition("unit_price", DecimalType(precision=10, scale=2),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
        ],
        table_constraints=[
            TableConstraint(
                constraint_type=TableConstraintType.PRIMARY_KEY,
                columns=["order_id", "product_id"],
            ),
        ],
    )


def create_store_inventory_table(dialect, table_name: str = "store_inventory") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("store_id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("product_id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("batch_id", VarCharType(64),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("stock", IntegerType(),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=0),
                ]),
        ],
        table_constraints=[
            TableConstraint(
                constraint_type=TableConstraintType.PRIMARY_KEY,
                columns=["store_id", "product_id", "batch_id"],
            ),
        ],
    )


def create_orders_table(dialect, table_name: str = "orders") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("total", DecimalType(precision=10, scale=2),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("created_at", TextType()),
            ColumnDefinition("updated_at", TextType()),
        ],
    )


TABLE_EXPRESSIONS: Dict[str, Callable] = {
    "order_items": create_order_items_table,
    "store_inventory": create_store_inventory_table,
    "orders": create_orders_table,
}
