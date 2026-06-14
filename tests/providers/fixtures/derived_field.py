# tests/providers/fixtures/derived_field.py
"""DDL expressions for the feature/derived_field table group."""

from typing import Callable, Dict

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    DropTableExpression,
    TableExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)


def create_product_table(dialect, table_name: str = "product") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect, table=table_name, if_not_exists=True,
        columns=[
            ColumnDefinition("id", "INTEGER", constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("name", "TEXT", constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("price", "REAL", constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("quantity", "INTEGER", constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
        ],
    )


def drop_table(dialect, table_name: str) -> DropTableExpression:
    return DropTableExpression(dialect=dialect, table=TableExpression(dialect, table_name), if_exists=True)


TABLE_EXPRESSIONS: Dict[str, Callable] = {
    "product": create_product_table,
}
