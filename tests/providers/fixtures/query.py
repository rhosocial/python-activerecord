# tests/providers/fixtures/query.py
"""
DDL expressions for the feature/query table group.
"""

from decimal import Decimal
from typing import Callable, Dict

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    DropTableExpression,
    TableExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
    ForeignKeyConstraint,
    RawSQLExpression,
)
from rhosocial.activerecord.backend.expression.statements import ReferentialAction
from rhosocial.activerecord.backend.expression.types import DecimalType, FloatType, IntegerType, TextType, TimestampType, VarCharType


def create_users_table(dialect, table_name: str = "users") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "username", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "email", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "age", IntegerType(dialect)),
            ColumnDefinition(dialect, "balance", FloatType(dialect),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=Decimal("0.00")),
                ]),
            ColumnDefinition(dialect, "is_active", IntegerType(dialect),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=1),
                ]),
            ColumnDefinition(dialect, "created_at", TextType(dialect)),
            ColumnDefinition(dialect, "updated_at", TextType(dialect)),
        ],
    )


def create_posts_table(dialect, table_name: str = "posts") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "user_id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "title", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "content", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "status", TextType(dialect),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="published"),
                ]),
            ColumnDefinition(dialect, "created_at", TextType(dialect)),
            ColumnDefinition(dialect, "updated_at", TextType(dialect)),
        ],
        table_constraints=[
            ForeignKeyConstraint(dialect, 
                columns=["user_id"],
                foreign_key_table="users",
                foreign_key_columns=["id"],
            ),
        ],
    )


def create_comments_table(dialect, table_name: str = "comments") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "user_id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "post_id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "content", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "is_hidden", IntegerType(dialect),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=0),
                ]),
            ColumnDefinition(dialect, "created_at", TextType(dialect)),
            ColumnDefinition(dialect, "updated_at", TextType(dialect)),
        ],
        table_constraints=[
            ForeignKeyConstraint(dialect, columns=["user_id"], foreign_key_table="users", foreign_key_columns=["id"]),
            ForeignKeyConstraint(dialect, columns=["post_id"], foreign_key_table="posts", foreign_key_columns=["id"]),
        ],
    )


def create_profiles_table(dialect, table_name: str = "profiles") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "user_id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "bio", TextType(dialect)),
            ColumnDefinition(dialect, "avatar_url", TextType(dialect)),
            ColumnDefinition(dialect, "created_at", TextType(dialect)),
            ColumnDefinition(dialect, "updated_at", TextType(dialect)),
        ],
        table_constraints=[
            ForeignKeyConstraint(dialect, columns=["user_id"], foreign_key_table="users", foreign_key_columns=["id"]),
        ],
    )


def create_orders_table(dialect, table_name: str = "orders") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "user_id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "order_number", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "total_amount", DecimalType(dialect, precision=10, scale=2),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=Decimal("0.00")),
                ]),
            ColumnDefinition(dialect, "status", TextType(dialect),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="pending"),
                ]),
            ColumnDefinition(dialect, "created_at", TextType(dialect)),
            ColumnDefinition(dialect, "updated_at", TextType(dialect)),
        ],
        table_constraints=[
            ForeignKeyConstraint(dialect, columns=["user_id"], foreign_key_table="users", foreign_key_columns=["id"]),
        ],
    )


def create_order_items_table(dialect, table_name: str = "order_items") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "order_id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "product_name", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "quantity", IntegerType(dialect),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=1),
                ]),
            ColumnDefinition(dialect, "unit_price", DecimalType(dialect, precision=10, scale=2),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "subtotal", DecimalType(dialect, precision=10, scale=2),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=Decimal("0.00")),
                ]),
            ColumnDefinition(dialect, "created_at", TextType(dialect)),
            ColumnDefinition(dialect, "updated_at", TextType(dialect)),
        ],
        table_constraints=[
            ForeignKeyConstraint(dialect, columns=["order_id"], foreign_key_table="orders", foreign_key_columns=["id"]),
        ],
    )


def create_extended_orders_table(dialect, table_name: str = "extended_orders") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "user_id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "order_number", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "total_amount", DecimalType(dialect, precision=10, scale=2),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=Decimal("0.00")),
                ]),
            ColumnDefinition(dialect, "status", TextType(dialect),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="pending"),
                ]),
            ColumnDefinition(dialect, "priority", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="medium")]),
            ColumnDefinition(dialect, "region", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="default")]),
            ColumnDefinition(dialect, "category", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="")]),
            ColumnDefinition(dialect, "product", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="")]),
            ColumnDefinition(dialect, "department", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="")]),
            ColumnDefinition(dialect, "year", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="")]),
            ColumnDefinition(dialect, "quarter", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="")]),
            ColumnDefinition(dialect, "created_at", TextType(dialect)),
            ColumnDefinition(dialect, "updated_at", TextType(dialect)),
        ],
        table_constraints=[
            ForeignKeyConstraint(dialect, columns=["user_id"], foreign_key_table="users", foreign_key_columns=["id"]),
        ],
    )


def create_extended_order_items_table(dialect, table_name: str = "extended_order_items") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "order_id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "product_name", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "quantity", IntegerType(dialect),
                constraints=[
                    ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=1),
                ]),
            ColumnDefinition(dialect, "price", DecimalType(dialect, precision=10, scale=2),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "category", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="")]),
            ColumnDefinition(dialect, "region", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value="")]),
            ColumnDefinition(dialect, "created_at", TextType(dialect)),
            ColumnDefinition(dialect, "updated_at", TextType(dialect)),
        ],
        table_constraints=[
            ForeignKeyConstraint(dialect, 
                columns=["order_id"], foreign_key_table="extended_orders", foreign_key_columns=["id"]
            ),
        ],
    )


def create_json_users_table(dialect, table_name: str = "json_users") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "username", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "email", TextType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "age", IntegerType(dialect)),
            ColumnDefinition(dialect, "settings", TextType(dialect)),
            ColumnDefinition(dialect, "tags", TextType(dialect)),
            ColumnDefinition(dialect, "profile", TextType(dialect)),
            ColumnDefinition(dialect, "roles", TextType(dialect)),
            ColumnDefinition(dialect, "scores", TextType(dialect)),
            ColumnDefinition(dialect, "subscription", TextType(dialect)),
            ColumnDefinition(dialect, "preferences", TextType(dialect)),
            ColumnDefinition(dialect, "created_at", TextType(dialect)),
            ColumnDefinition(dialect, "updated_at", TextType(dialect)),
        ],
    )


def create_searchable_items_table(dialect, table_name: str = "searchable_items") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(dialect, "name", TextType(dialect)),
            ColumnDefinition(dialect, "tags", TextType(dialect)),
        ],
    )


def create_nodes_table(dialect, table_name: str = "nodes") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=True,
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition(dialect, "name", VarCharType(dialect, 100),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dialect, "parent_id", IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=RawSQLExpression(dialect, "NULL"))]),
            ColumnDefinition(dialect, "value", DecimalType(dialect, precision=10, scale=2),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=Decimal("0.00"))]),
            ColumnDefinition(dialect, "created_at", TimestampType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=RawSQLExpression(dialect, "CURRENT_TIMESTAMP"))]),
            ColumnDefinition(dialect, "updated_at", TimestampType(dialect),
                constraints=[ColumnConstraint(dialect, ColumnConstraintType.DEFAULT, default_value=RawSQLExpression(dialect, "CURRENT_TIMESTAMP"))]),
        ],
        table_constraints=[
            ForeignKeyConstraint(dialect, 
                columns=["parent_id"],
                foreign_key_table="nodes",
                foreign_key_columns=["id"],
                on_delete=ReferentialAction.CASCADE,
            ),
        ],
    )


def drop_table(dialect, table_name: str) -> DropTableExpression:
    return DropTableExpression(
        dialect=dialect,
        table=TableExpression(dialect, table_name),
        if_exists=True,
    )


TABLE_EXPRESSIONS: Dict[str, Callable] = {
    "users": create_users_table,
    "posts": create_posts_table,
    "comments": create_comments_table,
    "profiles": create_profiles_table,
    "orders": create_orders_table,
    "order_items": create_order_items_table,
    "extended_orders": create_extended_orders_table,
    "extended_order_items": create_extended_order_items_table,
    "json_users": create_json_users_table,
    "searchable_items": create_searchable_items_table,
    "nodes": create_nodes_table,
}
