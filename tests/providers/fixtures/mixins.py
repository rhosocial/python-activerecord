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
from rhosocial.activerecord.backend.expression.types import FloatType, IntegerType, TextType
from typing import Callable, Dict
# tests/providers/fixtures/mixins.py
"""
DDL expressions for the feature/mixins table group.
"""




def create_timestamped_posts_table(dialect, table_name: str = "timestamped_posts") -> CreateTableStatement:
    return CreateTableStatement(
        dialect=dialect,
        table=Table(dialect, table_name),
        if_not_exists=True,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect, is_auto_increment=True))]),
            ColumnDefinition(dialect, "title", TextType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]),
            ColumnDefinition(dialect, "content", TextType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]),
            ColumnDefinition(dialect, "created_at", TextType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]),
            ColumnDefinition(dialect, "updated_at", TextType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]),
        ],
    )


def create_versioned_products_table(dialect, table_name: str = "versioned_products") -> CreateTableStatement:
    return CreateTableStatement(
        dialect=dialect,
        table=Table(dialect, table_name),
        if_not_exists=True,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect, is_auto_increment=True))]),
            ColumnDefinition(dialect, "name", TextType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]),
            ColumnDefinition(dialect, "price", FloatType(dialect),
                constraints=[
                    ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
                    ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, 0.0)),
                ]),
            ColumnDefinition(dialect, "version", IntegerType(dialect),
                constraints=[
                    ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
                    ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, 1)),
                ]),
        ],
    )


def create_tasks_table(dialect, table_name: str = "tasks") -> CreateTableStatement:
    return CreateTableStatement(
        dialect=dialect,
        table=Table(dialect, table_name),
        if_not_exists=True,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect, is_auto_increment=True))]),
            ColumnDefinition(dialect, "title", TextType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]),
            ColumnDefinition(dialect, "is_completed", IntegerType(dialect),
                constraints=[
                    ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
                    ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, 0)),
                ]),
            ColumnDefinition(dialect, "deleted_at", TextType(dialect)),
        ],
    )


def create_combined_articles_table(dialect, table_name: str = "combined_articles") -> CreateTableStatement:
    return CreateTableStatement(
        dialect=dialect,
        table=Table(dialect, table_name),
        if_not_exists=True,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect, is_auto_increment=True))]),
            ColumnDefinition(dialect, "title", TextType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]),
            ColumnDefinition(dialect, "content", TextType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]),
            ColumnDefinition(dialect, "status", TextType(dialect),
                constraints=[
                    ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
                    ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, "draft")),
                ]),
            ColumnDefinition(dialect, "version", IntegerType(dialect),
                constraints=[
                    ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
                    ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, 1)),
                ]),
            ColumnDefinition(dialect, "created_at", TextType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]),
            ColumnDefinition(dialect, "updated_at", TextType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]),
            ColumnDefinition(dialect, "deleted_at", TextType(dialect)),
        ],
    )


def drop_table(dialect, table_name: str) -> DropTableStatement:
    return DropTableStatement(
        dialect=dialect,
        table=Table(dialect, table_name),
        if_exists=True,
    )


TABLE_EXPRESSIONS: Dict[str, Callable] = {
    "timestamped_posts": create_timestamped_posts_table,
    "versioned_products": create_versioned_products_table,
    "tasks": create_tasks_table,
    "combined_articles": create_combined_articles_table,
}
