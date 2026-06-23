# tests/providers/fixtures/relation.py
"""DDL expressions for the feature/relation table group."""

from typing import Callable, Dict

from rhosocial.activerecord.backend.expression.types import IntegerType, TextType
from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    DropTableExpression,
    TableExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
    ForeignKeyConstraint,
)


def create_employees_table(dialect, table_name: str = "employees") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect, table=table_name, if_not_exists=True,
        columns=[
            ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("username", TextType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("department_id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
        ],
        table_constraints=[ForeignKeyConstraint(columns=["department_id"], foreign_key_table="departments", foreign_key_columns=["id"])],
    )


def create_departments_table(dialect, table_name: str = "departments") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect, table=table_name, if_not_exists=True,
        columns=[
            ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("name", TextType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("description", TextType(), constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="")]),
        ],
    )


def create_authors_table(dialect, table_name: str = "authors") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect, table=table_name, if_not_exists=True,
        columns=[
            ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("name", TextType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
        ],
    )


def create_books_table(dialect, table_name: str = "books") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect, table=table_name, if_not_exists=True,
        columns=[
            ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("title", TextType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("author_id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
        ],
        table_constraints=[ForeignKeyConstraint(columns=["author_id"], foreign_key_table="authors", foreign_key_columns=["id"])],
    )


def create_chapters_table(dialect, table_name: str = "chapters") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect, table=table_name, if_not_exists=True,
        columns=[
            ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("title", TextType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("book_id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
        ],
        table_constraints=[ForeignKeyConstraint(columns=["book_id"], foreign_key_table="books", foreign_key_columns=["id"])],
    )


def create_profiles_table(dialect, table_name: str = "profiles") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect, table=table_name, if_not_exists=True,
        columns=[
            ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("bio", TextType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("author_id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
        ],
        table_constraints=[ForeignKeyConstraint(columns=["author_id"], foreign_key_table="authors", foreign_key_columns=["id"])],
    )


def create_rl_users_table(dialect, table_name: str = "users") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect, table=table_name, if_not_exists=True,
        columns=[
            ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("name", TextType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("email", TextType()),
            ColumnDefinition("settings", TextType()),
        ],
    )


def create_rl_posts_table(dialect, table_name: str = "posts") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect, table=table_name, if_not_exists=True,
        columns=[
            ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("title", TextType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("body", TextType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("user_id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("view_count", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL), ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=0)]),
            ColumnDefinition("metadata", TextType()),
        ],
        table_constraints=[ForeignKeyConstraint(columns=["user_id"], foreign_key_table="users", foreign_key_columns=["id"])],
    )


def create_rl_comments_table(dialect, table_name: str = "comments") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect, table=table_name, if_not_exists=True,
        columns=[
            ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("body", TextType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("post_id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("meta", TextType()),
        ],
        table_constraints=[ForeignKeyConstraint(columns=["post_id"], foreign_key_table="posts", foreign_key_columns=["id"])],
    )


def create_relation_boundary_owners_table(dialect, table_name: str = "relation_boundary_owners") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect, table=table_name, if_not_exists=True,
        columns=[
            ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("name", TextType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
        ],
    )


def create_relation_boundary_profiles_table(dialect, table_name: str = "relation_boundary_profiles") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect, table=table_name, if_not_exists=True,
        columns=[
            ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("bio", TextType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("owner_id", IntegerType()),
        ],
    )


def create_relation_boundary_posts_table(dialect, table_name: str = "relation_boundary_posts") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect, table=table_name, if_not_exists=True,
        columns=[
            ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("title", TextType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("owner_id", IntegerType()),
        ],
    )


def drop_table(dialect, table_name: str) -> DropTableExpression:
    return DropTableExpression(dialect=dialect, table=TableExpression(dialect, table_name), if_exists=True)


TABLE_EXPRESSIONS: Dict[str, Callable] = {
    "employees": create_employees_table,
    "departments": create_departments_table,
    "authors": create_authors_table,
    "books": create_books_table,
    "chapters": create_chapters_table,
    "profiles": create_profiles_table,
    "users": create_rl_users_table,
    "posts": create_rl_posts_table,
    "comments": create_rl_comments_table,
    "relation_boundary_owners": create_relation_boundary_owners_table,
    "relation_boundary_profiles": create_relation_boundary_profiles_table,
    "relation_boundary_posts": create_relation_boundary_posts_table,
}
