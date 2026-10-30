from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefaultConstraint,
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression import (
    CreateTableStatement,
    DropTableStatement,
    ColumnDefinition,
    ColumnConstraint,
)
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType
from typing import Callable, Dict
# tests/providers/fixtures/events.py
"""
DDL expressions for the feature/events table group.

Each function returns a CreateTableStatement matching the .sql schema file.
"""




def create_event_tests_table(dialect, table_name: str = "event_tests") -> CreateTableStatement:
    return CreateTableStatement(
        dialect=dialect,
        table=Table(dialect, table_name),
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect, is_auto_increment=True))]),
            ColumnDefinition(dialect, "name", TextType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]),
            ColumnDefinition(dialect, "status", TextType(dialect),
                constraints=[
                    ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
                    ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, "draft")),
                ]),
            ColumnDefinition(dialect, "revision", IntegerType(dialect),
                constraints=[
                    ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
                    ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, 1)),
                ]),
            ColumnDefinition(dialect, "content", TextType(dialect)),
            ColumnDefinition(dialect, "created_at", TextType(dialect)),
            ColumnDefinition(dialect, "updated_at", TextType(dialect)),
        ],
    )


def create_event_test_models_table(dialect, table_name: str = "event_test_models") -> CreateTableStatement:
    return CreateTableStatement(
        dialect=dialect,
        table=Table(dialect, table_name),
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect, is_auto_increment=True))]),
            ColumnDefinition(dialect, "name", TextType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]),
            ColumnDefinition(dialect, "description", TextType(dialect)),
            ColumnDefinition(dialect, "status", TextType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, "active"))]),
            ColumnDefinition(dialect, "event_log", TextType(dialect)),
            ColumnDefinition(dialect, "created_at", TextType(dialect)),
            ColumnDefinition(dialect, "updated_at", TextType(dialect)),
        ],
    )


def create_event_tracking_models_table(dialect, table_name: str = "event_tracking_models") -> CreateTableStatement:
    return CreateTableStatement(
        dialect=dialect,
        table=Table(dialect, table_name),
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect, is_auto_increment=True))]),
            ColumnDefinition(dialect, "title", TextType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]),
            ColumnDefinition(dialect, "content", TextType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]),
            ColumnDefinition(dialect, "view_count", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, 0))]),
            ColumnDefinition(dialect, "last_viewed_at", TextType(dialect)),
        ],
    )


def drop_table(dialect, table_name: str) -> DropTableStatement:
    return DropTableStatement(
        dialect=dialect,
        table=Table(dialect, table_name),
        if_exists=True,
    )


TABLE_EXPRESSIONS: Dict[str, Callable] = {
    "event_tests": create_event_tests_table,
    "event_test_models": create_event_test_models_table,
    "event_tracking_models": create_event_tracking_models_table,
}
