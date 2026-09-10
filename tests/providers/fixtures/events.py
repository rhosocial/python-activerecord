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
            ColumnDefinition(dialect, "id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "name", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "status", TextType(),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="draft"),
                ]),
            ColumnDefinition(dialect, "revision", IntegerType(),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=1),
                ]),
            ColumnDefinition(dialect, "content", TextType()),
            ColumnDefinition(dialect, "created_at", TextType()),
            ColumnDefinition(dialect, "updated_at", TextType()),
        ],
    )


def create_event_test_models_table(dialect, table_name: str = "event_test_models") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "name", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "description", TextType()),
            ColumnDefinition(dialect, "status", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="active")]),
            ColumnDefinition(dialect, "event_log", TextType()),
            ColumnDefinition(dialect, "created_at", TextType()),
            ColumnDefinition(dialect, "updated_at", TextType()),
        ],
    )


def create_event_tracking_models_table(dialect, table_name: str = "event_tracking_models") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "title", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "content", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "view_count", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=0)]),
            ColumnDefinition(dialect, "last_viewed_at", TextType()),
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
