# tests/providers/fixtures/events.py
"""
DDL expressions for the feature/events table group.

Each function returns a CreateTableExpression matching the .sql schema file.
"""

from typing import Callable, Dict

from rhosocial.activerecord.backend.expression.types import IntegerType, TextType
from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    DropTableExpression,
    TableExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)


def create_event_tests_table(dialect, table_name: str = "event_tests") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("name", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("status", TextType(),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="draft"),
                ]),
            ColumnDefinition("revision", IntegerType(),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=1),
                ]),
            ColumnDefinition("content", TextType()),
            ColumnDefinition("created_at", TextType()),
            ColumnDefinition("updated_at", TextType()),
        ],
    )


def create_event_test_models_table(dialect, table_name: str = "event_test_models") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("name", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("description", TextType()),
            ColumnDefinition("status", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="active")]),
            ColumnDefinition("event_log", TextType()),
            ColumnDefinition("created_at", TextType()),
            ColumnDefinition("updated_at", TextType()),
        ],
    )


def create_event_tracking_models_table(dialect, table_name: str = "event_tracking_models") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("title", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("content", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("view_count", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=0)]),
            ColumnDefinition("last_viewed_at", TextType()),
        ],
    )


def drop_table(dialect, table_name: str) -> DropTableExpression:
    return DropTableExpression(
        dialect=dialect,
        table=TableExpression(dialect, table_name),
        if_exists=True,
    )


TABLE_EXPRESSIONS: Dict[str, Callable] = {
    "event_tests": create_event_tests_table,
    "event_test_models": create_event_test_models_table,
    "event_tracking_models": create_event_tracking_models_table,
}
