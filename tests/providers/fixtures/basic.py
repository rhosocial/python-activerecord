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

from rhosocial.activerecord.backend.expression.types import BlobType, BooleanType, DateTimeType, FloatType, IntegerType, TextType, VarCharType
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
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("username", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("email", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("age", IntegerType()),
            ColumnDefinition("balance", FloatType(),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=0.0),
                ]),
            ColumnDefinition("is_active", BooleanType(),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=1),
                ]),
            ColumnDefinition("created_at", TextType()),
            ColumnDefinition("updated_at", TextType()),
        ],
    )


def create_type_cases_table(dialect, table_name: str = "type_cases") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("username", TextType()),
            ColumnDefinition("email", TextType()),
            ColumnDefinition("tiny_int", IntegerType()),
            ColumnDefinition("small_int", IntegerType()),
            ColumnDefinition("big_int", IntegerType()),
            ColumnDefinition("float_val", FloatType()),
            ColumnDefinition("double_val", FloatType()),
            ColumnDefinition("decimal_val", FloatType()),
            ColumnDefinition("char_val", TextType()),
            ColumnDefinition("varchar_val", TextType()),
            ColumnDefinition("text_val", TextType()),
            ColumnDefinition("date_val", TextType()),
            ColumnDefinition("time_val", TextType()),
            ColumnDefinition("timestamp_val", TextType()),
            ColumnDefinition("blob_val", BlobType()),
            ColumnDefinition("json_val", TextType()),
            ColumnDefinition("array_val", TextType()),
            ColumnDefinition("is_active", BooleanType()),
        ],
    )


def create_type_tests_table(dialect, table_name: str = "type_tests") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("string_field", TextType()),
            ColumnDefinition("int_field", IntegerType()),
            ColumnDefinition("float_field", FloatType()),
            ColumnDefinition("decimal_field", FloatType()),
            ColumnDefinition("bool_field", BooleanType()),
            ColumnDefinition("datetime_field", TextType()),
            ColumnDefinition("json_field", TextType()),
            ColumnDefinition("nullable_field", TextType()),
        ],
    )


def create_validated_field_users_table(dialect, table_name: str = "validated_field_users") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("username", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("email", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("age", IntegerType()),
            ColumnDefinition("balance", FloatType()),
            ColumnDefinition("credit_score", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("status", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("is_active", BooleanType()),
        ],
    )


def create_validated_users_table(dialect, table_name: str = "validated_users") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("username", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("email", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("age", IntegerType()),
        ],
    )


def create_pydantic_validated_models_table(dialect, table_name: str = "pydantic_validated_models") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("code", TextType()),
            ColumnDefinition("quantity", IntegerType()),
            ColumnDefinition("step_count", IntegerType()),
            ColumnDefinition("price", FloatType()),
            ColumnDefinition("start_at", TextType()),
            ColumnDefinition("end_at", TextType()),
            ColumnDefinition("status", TextType()),
            ColumnDefinition("normalized_name", TextType()),
            ColumnDefinition("created_token", TextType()),
        ],
    )


def create_bulk_users_table(dialect, table_name: str = "bulk_users") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("name", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("age", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=0)]),
            ColumnDefinition("email", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="")]),
        ],
    )


def create_posts_table(dialect, table_name: str = "posts") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=True,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("author", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("title", VarCharType(255),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("content", TextType()),
            ColumnDefinition("published_at", DateTimeType()),
            ColumnDefinition("published", BooleanType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=False)]),
            ColumnDefinition("created_at", DateTimeType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("updated_at", DateTimeType()),
        ],
    )


def create_comments_table(dialect, table_name: str = "comments") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=True,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("post_ref", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("author", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("text", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("created_at", DateTimeType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("updated_at", DateTimeType()),
            ColumnDefinition("approved", BooleanType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=False)]),
        ],
    )


def create_column_mapping_items_table(dialect, table_name: str = "column_mapping_items") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("name", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("item_total", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("remarks", IntegerType()),
        ],
    )


def create_mixed_annotation_items_table(dialect, table_name: str = "mixed_annotation_items") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("name", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("tags", TextType()),
            ColumnDefinition("meta", TextType()),
            ColumnDefinition("description", TextType()),
            ColumnDefinition("status", TextType()),
        ],
    )


def create_type_adapter_tests_table(dialect, table_name: str = "type_adapter_tests") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=True,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("name", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("optional_name", TextType()),
            ColumnDefinition("optional_age", IntegerType()),
            ColumnDefinition("last_login", TextType()),
            ColumnDefinition("is_premium", IntegerType()),
            ColumnDefinition("unsupported_union", TextType()),
            ColumnDefinition("custom_bool", TextType()),
            ColumnDefinition("optional_custom_bool", TextType()),
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
