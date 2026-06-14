# tests/providers/fixtures/basic.py
"""
DDL expressions for the feature/basic table group.

Each function returns a ProcedureGraph containing the CREATE TABLE
expression (and optionally DROP TABLE for teardown).

These are used in two ways:
1. Comparison tests: compile to SQL and compare against existing .sql files
2. Eventually: replace .sql files entirely
"""

from typing import Callable, Dict

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    DropTableExpression,
    TableExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)


def create_users_table(dialect, table_name: str = "users") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("username", "TEXT",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("email", "TEXT",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("age", "INTEGER"),
            ColumnDefinition("balance", "REAL",
                constraints=[
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=0.0),
                ]),
            ColumnDefinition("is_active", "BOOLEAN",
                constraints=[
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=1),
                ]),
            ColumnDefinition("created_at", "TEXT"),
            ColumnDefinition("updated_at", "TEXT"),
        ],
    )


def create_type_cases_table(dialect, table_name: str = "type_cases") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", "TEXT",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("username", "TEXT"),
            ColumnDefinition("email", "TEXT"),
            ColumnDefinition("tiny_int", "INTEGER"),
            ColumnDefinition("small_int", "INTEGER"),
            ColumnDefinition("big_int", "INTEGER"),
            ColumnDefinition("float_val", "REAL"),
            ColumnDefinition("double_val", "REAL"),
            ColumnDefinition("decimal_val", "REAL"),
            ColumnDefinition("char_val", "TEXT"),
            ColumnDefinition("varchar_val", "TEXT"),
            ColumnDefinition("text_val", "TEXT"),
            ColumnDefinition("date_val", "TEXT"),
            ColumnDefinition("time_val", "TEXT"),
            ColumnDefinition("timestamp_val", "TEXT"),
            ColumnDefinition("blob_val", "BLOB"),
            ColumnDefinition("json_val", "TEXT"),
            ColumnDefinition("array_val", "TEXT"),
            ColumnDefinition("is_active", "BOOLEAN"),
        ],
    )


def create_type_tests_table(dialect, table_name: str = "type_tests") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", "TEXT",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("string_field", "TEXT"),
            ColumnDefinition("int_field", "INTEGER"),
            ColumnDefinition("float_field", "REAL"),
            ColumnDefinition("decimal_field", "REAL"),
            ColumnDefinition("bool_field", "BOOLEAN"),
            ColumnDefinition("datetime_field", "TEXT"),
            ColumnDefinition("json_field", "TEXT"),
            ColumnDefinition("nullable_field", "TEXT"),
        ],
    )


def create_validated_field_users_table(dialect, table_name: str = "validated_field_users") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("username", "TEXT",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("email", "TEXT",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("age", "INTEGER"),
            ColumnDefinition("balance", "REAL"),
            ColumnDefinition("credit_score", "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("status", "TEXT",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("is_active", "BOOLEAN"),
        ],
    )


def create_validated_users_table(dialect, table_name: str = "validated_users") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("username", "TEXT",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("email", "TEXT",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("age", "INTEGER"),
        ],
    )


def create_pydantic_validated_models_table(dialect, table_name: str = "pydantic_validated_models") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("code", "TEXT"),
            ColumnDefinition("quantity", "INTEGER"),
            ColumnDefinition("step_count", "INTEGER"),
            ColumnDefinition("price", "REAL"),
            ColumnDefinition("start_at", "TEXT"),
            ColumnDefinition("end_at", "TEXT"),
            ColumnDefinition("status", "TEXT"),
            ColumnDefinition("normalized_name", "TEXT"),
            ColumnDefinition("created_token", "TEXT"),
        ],
    )


def create_bulk_users_table(dialect, table_name: str = "bulk_users") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("name", "TEXT",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("age", "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=0)]),
            ColumnDefinition("email", "TEXT",
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="")]),
        ],
    )


def create_posts_table(dialect, table_name: str = "posts") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=True,
        columns=[
            ColumnDefinition("id", "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("author", "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("title", "VARCHAR(255)",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("content", "TEXT"),
            ColumnDefinition("published_at", "DATETIME"),
            ColumnDefinition("published", "BOOLEAN",
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=False)]),
            ColumnDefinition("created_at", "DATETIME",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("updated_at", "DATETIME"),
        ],
    )


def create_comments_table(dialect, table_name: str = "comments") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=True,
        columns=[
            ColumnDefinition("id", "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("post_ref", "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("author", "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("text", "TEXT",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("created_at", "DATETIME",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("updated_at", "DATETIME"),
            ColumnDefinition("approved", "BOOLEAN",
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=False)]),
        ],
    )


def create_column_mapping_items_table(dialect, table_name: str = "column_mapping_items") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("name", "TEXT",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("item_total", "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("remarks", "INTEGER"),
        ],
    )


def create_mixed_annotation_items_table(dialect, table_name: str = "mixed_annotation_items") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("name", "TEXT",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("tags", "TEXT"),
            ColumnDefinition("meta", "TEXT"),
            ColumnDefinition("description", "TEXT"),
            ColumnDefinition("status", "TEXT"),
        ],
    )


def create_type_adapter_tests_table(dialect, table_name: str = "type_adapter_tests") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=True,
        columns=[
            ColumnDefinition("id", "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("name", "TEXT",
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("optional_name", "TEXT"),
            ColumnDefinition("optional_age", "INTEGER"),
            ColumnDefinition("last_login", "TEXT"),
            ColumnDefinition("is_premium", "INTEGER"),
            ColumnDefinition("unsupported_union", "TEXT"),
            ColumnDefinition("custom_bool", "TEXT"),
            ColumnDefinition("optional_custom_bool", "TEXT"),
        ],
    )


def drop_table(dialect, table_name: str) -> DropTableExpression:
    """通用 DROP TABLE 表达式，供 Provider 调用。"""
    return DropTableExpression(
        dialect=dialect,
        table=TableExpression(dialect, table_name),
        if_exists=True,
    )


TABLE_EXPRESSIONS: Dict[str, Callable] = {
    "users": create_users_table,
    "type_cases": create_type_cases_table,
    "type_tests": create_type_tests_table,
    "validated_field_users": create_validated_field_users_table,
    "validated_users": create_validated_users_table,
    "pydantic_validated_models": create_pydantic_validated_models_table,
    "bulk_users": create_bulk_users_table,
    "posts": create_posts_table,
    "comments": create_comments_table,
    "column_mapping_items": create_column_mapping_items_table,
    "mixed_annotation_items": create_mixed_annotation_items_table,
    "type_adapter_tests": create_type_adapter_tests_table,
}
