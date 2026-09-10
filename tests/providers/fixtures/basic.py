# tests/providers/fixtures/basic.py
"""
DDL expressions for the feature/basic table group.

Each function returns a ProcedureGraph containing the CREATE TABLE
expression (and optionally DROP TABLE for teardown).

These are used in two ways:
1. Comparison tests: compile to SQL and compare against existing .sql files
2. Eventually: replace .sql files entirely
"""

from decimal import Decimal
from typing import Callable, Dict

from rhosocial.activerecord.backend.expression.types import BlobType, BooleanType, DateTimeType, DecimalType, FloatType, IntegerType, TextType, VarCharType
from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    DropTableExpression,
    TableExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
    TableConstraint,
    TableConstraintType,
)


def create_users_table(dialect, table_name: str = "users") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "username", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "email", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "age", IntegerType()),
            ColumnDefinition(dialect, "balance", FloatType(),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=0.0),
                ]),
            ColumnDefinition(dialect, "is_active", BooleanType(),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=1),
                ]),
            ColumnDefinition(dialect, "created_at", TextType()),
            ColumnDefinition(dialect, "updated_at", TextType()),
        ],
    )


def create_type_cases_table(dialect, table_name: str = "type_cases") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(dialect, "username", TextType()),
            ColumnDefinition(dialect, "email", TextType()),
            ColumnDefinition(dialect, "tiny_int", IntegerType()),
            ColumnDefinition(dialect, "small_int", IntegerType()),
            ColumnDefinition(dialect, "big_int", IntegerType()),
            ColumnDefinition(dialect, "float_val", FloatType()),
            ColumnDefinition(dialect, "double_val", FloatType()),
            ColumnDefinition(dialect, "decimal_val", FloatType()),
            ColumnDefinition(dialect, "char_val", TextType()),
            ColumnDefinition(dialect, "varchar_val", TextType()),
            ColumnDefinition(dialect, "text_val", TextType()),
            ColumnDefinition(dialect, "date_val", TextType()),
            ColumnDefinition(dialect, "time_val", TextType()),
            ColumnDefinition(dialect, "timestamp_val", TextType()),
            ColumnDefinition(dialect, "blob_val", BlobType()),
            ColumnDefinition(dialect, "json_val", TextType()),
            ColumnDefinition(dialect, "array_val", TextType()),
            ColumnDefinition(dialect, "is_active", BooleanType()),
        ],
    )


def create_type_tests_table(dialect, table_name: str = "type_tests") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(dialect, "string_field", TextType()),
            ColumnDefinition(dialect, "int_field", IntegerType()),
            ColumnDefinition(dialect, "float_field", FloatType()),
            ColumnDefinition(dialect, "decimal_field", FloatType()),
            ColumnDefinition(dialect, "bool_field", BooleanType()),
            ColumnDefinition(dialect, "datetime_field", TextType()),
            ColumnDefinition(dialect, "json_field", TextType()),
            ColumnDefinition(dialect, "nullable_field", TextType()),
        ],
    )


def create_validated_field_users_table(dialect, table_name: str = "validated_field_users") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "username", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "email", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "age", IntegerType()),
            ColumnDefinition(dialect, "balance", FloatType()),
            ColumnDefinition(dialect, "credit_score", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "status", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "is_active", BooleanType()),
        ],
    )


def create_validated_users_table(dialect, table_name: str = "validated_users") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "username", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "email", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "age", IntegerType()),
        ],
    )


def create_pydantic_validated_models_table(dialect, table_name: str = "pydantic_validated_models") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "code", TextType()),
            ColumnDefinition(dialect, "quantity", IntegerType()),
            ColumnDefinition(dialect, "step_count", IntegerType()),
            ColumnDefinition(dialect, "price", FloatType()),
            ColumnDefinition(dialect, "start_at", TextType()),
            ColumnDefinition(dialect, "end_at", TextType()),
            ColumnDefinition(dialect, "status", TextType()),
            ColumnDefinition(dialect, "normalized_name", TextType()),
            ColumnDefinition(dialect, "created_token", TextType()),
        ],
    )


def create_bulk_users_table(dialect, table_name: str = "bulk_users") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "name", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "age", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=0)]),
            ColumnDefinition(dialect, "email", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="")]),
        ],
    )


def create_posts_table(dialect, table_name: str = "posts") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=True,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "author", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "title", VarCharType(255),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "content", TextType()),
            ColumnDefinition(dialect, "published_at", DateTimeType()),
            ColumnDefinition(dialect, "published", BooleanType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=False)]),
            ColumnDefinition(dialect, "created_at", DateTimeType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "updated_at", DateTimeType()),
        ],
    )


def create_comments_table(dialect, table_name: str = "comments") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=True,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "post_ref", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "author", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "text", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "created_at", DateTimeType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "updated_at", DateTimeType()),
            ColumnDefinition(dialect, "approved", BooleanType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=False)]),
        ],
    )


def create_column_mapping_items_table(dialect, table_name: str = "column_mapping_items") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "name", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "item_total", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "remarks", IntegerType()),
        ],
    )


def create_mixed_annotation_items_table(dialect, table_name: str = "mixed_annotation_items") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(dialect, "name", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "tags", TextType()),
            ColumnDefinition(dialect, "meta", TextType()),
            ColumnDefinition(dialect, "description", TextType()),
            ColumnDefinition(dialect, "status", TextType()),
        ],
    )


def create_type_adapter_tests_table(dialect, table_name: str = "type_adapter_tests") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=True,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "name", TextType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "optional_name", TextType()),
            ColumnDefinition(dialect, "optional_age", IntegerType()),
            ColumnDefinition(dialect, "last_login", TextType()),
            ColumnDefinition(dialect, "is_premium", IntegerType()),
            ColumnDefinition(dialect, "unsupported_union", TextType()),
            ColumnDefinition(dialect, "custom_bool", TextType()),
            ColumnDefinition(dialect, "optional_custom_bool", TextType()),
        ],
    )


def drop_table(dialect, table_name: str) -> DropTableExpression:
    """通用 DROP TABLE 表达式，供 Provider 调用。"""
    return DropTableExpression(
        dialect=dialect,
        table=TableExpression(dialect, table_name),
        if_exists=True,
    )


def create_composite_pk_order_items_table(dialect, table_name: str = "order_items") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "order_id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "product_id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "quantity", IntegerType(),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=1),
                ]),
            ColumnDefinition(dialect, "unit_price", DecimalType(precision=10, scale=2),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
        ],
        table_constraints=[
            TableConstraint(dialect, 
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
            ColumnDefinition(dialect, "store_id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "product_id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "batch_id", VarCharType(64),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "stock", IntegerType(),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=0),
                ]),
        ],
        table_constraints=[
            TableConstraint(dialect, 
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
            ColumnDefinition(dialect, "id", IntegerType(),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "total", DecimalType(precision=10, scale=2),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "created_at", TextType()),
            ColumnDefinition(dialect, "updated_at", TextType()),
        ],
    )


def create_product_table(dialect, table_name: str = "product") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect, table=table_name, if_not_exists=True,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(), constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "name", TextType(), constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "price", FloatType(), constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "quantity", IntegerType(), constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
        ],
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
    "order_items": create_composite_pk_order_items_table,
    "store_inventory": create_store_inventory_table,
    "orders": create_orders_table,
    "product": create_product_table,
}
