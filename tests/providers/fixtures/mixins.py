# tests/providers/fixtures/mixins.py
"""
DDL expressions for the feature/mixins table group.
"""

from typing import Callable, Dict

from rhosocial.activerecord.backend.expression.types import FloatType, IntegerType, TextType
from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    DropTableExpression,
    TableExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)


def create_timestamped_posts_table(dialect, table_name: str = "timestamped_posts") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=True,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "title", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "content", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "created_at", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "updated_at", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
        ],
    )


def create_versioned_products_table(dialect, table_name: str = "versioned_products") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=True,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "name", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "price", FloatType(),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=0.0),
                ]),
            ColumnDefinition(dialect, "version", IntegerType(),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=1),
                ]),
        ],
    )


def create_tasks_table(dialect, table_name: str = "tasks") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=True,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "title", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "is_completed", IntegerType(),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=0),
                ]),
            ColumnDefinition(dialect, "deleted_at", TextType()),
        ],
    )


def create_combined_articles_table(dialect, table_name: str = "combined_articles") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=True,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "title", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "content", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "status", TextType(),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="draft"),
                ]),
            ColumnDefinition(dialect, "version", IntegerType(),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=1),
                ]),
            ColumnDefinition(dialect, "created_at", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "updated_at", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "deleted_at", TextType()),
        ],
    )


def drop_table(dialect, table_name: str) -> DropTableExpression:
    return DropTableExpression(
        dialect=dialect,
        table=TableExpression(dialect, table_name),
        if_exists=True,
    )


TABLE_EXPRESSIONS: Dict[str, Callable] = {
    "timestamped_posts": create_timestamped_posts_table,
    "versioned_products": create_versioned_products_table,
    "tasks": create_tasks_table,
    "combined_articles": create_combined_articles_table,
}
