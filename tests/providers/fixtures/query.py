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
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=Decimal("0.00")),
                ]),
            ColumnDefinition("is_active", IntegerType(),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=1),
                ]),
            ColumnDefinition("created_at", TextType()),
            ColumnDefinition("updated_at", TextType()),
        ],
    )


def create_posts_table(dialect, table_name: str = "posts") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("user_id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("title", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("content", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("status", TextType(),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="published"),
                ]),
            ColumnDefinition("created_at", TextType()),
            ColumnDefinition("updated_at", TextType()),
        ],
        table_constraints=[
            ForeignKeyConstraint(
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
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("user_id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("post_id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("content", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("is_hidden", IntegerType(),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=0),
                ]),
            ColumnDefinition("created_at", TextType()),
            ColumnDefinition("updated_at", TextType()),
        ],
        table_constraints=[
            ForeignKeyConstraint(columns=["user_id"], foreign_key_table="users", foreign_key_columns=["id"]),
            ForeignKeyConstraint(columns=["post_id"], foreign_key_table="posts", foreign_key_columns=["id"]),
        ],
    )


def create_profiles_table(dialect, table_name: str = "profiles") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("user_id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("bio", TextType()),
            ColumnDefinition("avatar_url", TextType()),
            ColumnDefinition("created_at", TextType()),
            ColumnDefinition("updated_at", TextType()),
        ],
        table_constraints=[
            ForeignKeyConstraint(columns=["user_id"], foreign_key_table="users", foreign_key_columns=["id"]),
        ],
    )


def create_orders_table(dialect, table_name: str = "orders") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("user_id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("order_number", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("total_amount", DecimalType(precision=10, scale=2),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=Decimal("0.00")),
                ]),
            ColumnDefinition("status", TextType(),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="pending"),
                ]),
            ColumnDefinition("created_at", TextType()),
            ColumnDefinition("updated_at", TextType()),
        ],
        table_constraints=[
            ForeignKeyConstraint(columns=["user_id"], foreign_key_table="users", foreign_key_columns=["id"]),
        ],
    )


def create_order_items_table(dialect, table_name: str = "order_items") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("order_id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("product_name", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("quantity", IntegerType(),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=1),
                ]),
            ColumnDefinition("unit_price", DecimalType(precision=10, scale=2),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("subtotal", DecimalType(precision=10, scale=2),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=Decimal("0.00")),
                ]),
            ColumnDefinition("created_at", TextType()),
            ColumnDefinition("updated_at", TextType()),
        ],
        table_constraints=[
            ForeignKeyConstraint(columns=["order_id"], foreign_key_table="orders", foreign_key_columns=["id"]),
        ],
    )


def create_extended_orders_table(dialect, table_name: str = "extended_orders") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("user_id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("order_number", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("total_amount", DecimalType(precision=10, scale=2),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=Decimal("0.00")),
                ]),
            ColumnDefinition("status", TextType(),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="pending"),
                ]),
            ColumnDefinition("priority", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="medium")]),
            ColumnDefinition("region", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="default")]),
            ColumnDefinition("category", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="")]),
            ColumnDefinition("product", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="")]),
            ColumnDefinition("department", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="")]),
            ColumnDefinition("year", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="")]),
            ColumnDefinition("quarter", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="")]),
            ColumnDefinition("created_at", TextType()),
            ColumnDefinition("updated_at", TextType()),
        ],
        table_constraints=[
            ForeignKeyConstraint(columns=["user_id"], foreign_key_table="users", foreign_key_columns=["id"]),
        ],
    )


def create_extended_order_items_table(dialect, table_name: str = "extended_order_items") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("order_id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("product_name", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("quantity", IntegerType(),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=1),
                ]),
            ColumnDefinition("price", DecimalType(precision=10, scale=2),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("category", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="")]),
            ColumnDefinition("region", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="")]),
            ColumnDefinition("created_at", TextType()),
            ColumnDefinition("updated_at", TextType()),
        ],
        table_constraints=[
            ForeignKeyConstraint(
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
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("username", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("email", TextType(),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("age", IntegerType()),
            ColumnDefinition("settings", TextType()),
            ColumnDefinition("tags", TextType()),
            ColumnDefinition("profile", TextType()),
            ColumnDefinition("roles", TextType()),
            ColumnDefinition("scores", TextType()),
            ColumnDefinition("subscription", TextType()),
            ColumnDefinition("preferences", TextType()),
            ColumnDefinition("created_at", TextType()),
            ColumnDefinition("updated_at", TextType()),
        ],
    )


def create_searchable_items_table(dialect, table_name: str = "searchable_items") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=False,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("name", TextType()),
            ColumnDefinition("tags", TextType()),
        ],
    )


def create_nodes_table(dialect, table_name: str = "nodes") -> CreateTableExpression:
    return CreateTableExpression(
        dialect=dialect,
        table=table_name,
        if_not_exists=True,
        columns=[
            ColumnDefinition("id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
            ColumnDefinition("name", VarCharType(100),
                constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("parent_id", IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=RawSQLExpression(dialect, "NULL"))]),
            ColumnDefinition("value", DecimalType(precision=10, scale=2),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=Decimal("0.00"))]),
            ColumnDefinition("created_at", TimestampType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=RawSQLExpression(dialect, "CURRENT_TIMESTAMP"))]),
            ColumnDefinition("updated_at", TimestampType(),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=RawSQLExpression(dialect, "CURRENT_TIMESTAMP"))]),
        ],
        table_constraints=[
            ForeignKeyConstraint(
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
