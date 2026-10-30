"""Chapter 3: Modeling Data - DDL Examples

Demonstrates DDL operations using the expression-based API:
1. Create table with various column types and constraints
2. Create table with IF NOT EXISTS
3. Create temporary table
4. Drop table
5. Alter table operations
6. Introspection to verify schema changes
"""

from typing import ClassVar

from rhosocial.activerecord.backend.expression import (
    AddColumnAction,
    AlterTableStatement,
    ColumnConstraint,
    ColumnDefinition,
    CreateTableStatement,
    DropColumnAction,
    DropTableStatement,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
    ColumnUniqueConstraint,
)
from rhosocial.activerecord.backend.expression.types import (
    BooleanType,
    FloatType,
    IntegerType,
    TextType,
    TimestampType,
    VarCharType,
)
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.model import ActiveRecord


class User(ActiveRecord):
    """User Model for DDL demo"""

    __table_name__ = "users"

    username: str
    email: str
    is_active: bool = True

    c: ClassVar[FieldProxy] = FieldProxy()


def print_table_list(introspector, label: str):
    """Helper to print table list with label."""
    print(f"--- {label} ---")
    tables = introspector.list_tables()
    for t in tables:
        print(f"  Table: {t.name}, Type: {t.table_type}")
    print()


def print_table_info(introspector, table_name: str, label: str):
    """Helper to print table info with label."""
    print(f"--- {label} ---")
    table_info = introspector.get_table_info(table_name)
    if table_info and table_info.columns:
        for col in table_info.columns:
            print(
                f"  Column: {col.name}, Type: {col.data_type}, "
                f"Nullable: {col.nullable}, PK: {col.is_primary_key}"
            )
    else:
        print(f"  Table '{table_name}' not found or has no columns")
    print()


def main():
    # 1. Configure Database (Use in-memory database)
    config = SQLiteConnectionConfig(database=":memory:")
    User.configure(config, SQLiteBackend)

    # Get dialect from backend
    dialect = User.__backend__.dialect
    backend = User.__backend__

    # Get introspector
    introspector = backend.introspector

    # ============================================================
    # Example 1: Create basic table
    # ============================================================
    user_columns = [
        ColumnDefinition(
            dialect,
            "id",
            IntegerType(dialect),
            constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect))],
        ),
        ColumnDefinition(
            dialect,
            "username",
            VarCharType(dialect, length=50),
            constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))],
        ),
        ColumnDefinition(
            dialect,
            "email",
            VarCharType(dialect, length=100),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
                ColumnConstraint(dialect, branch=ColumnUniqueConstraint(dialect)),
            ],
        ),
        ColumnDefinition(dialect, "is_active", BooleanType(dialect)),
        ColumnDefinition(dialect, "created_at", TimestampType(dialect)),
    ]

    create_users = CreateTableStatement(dialect, Table(dialect, "users"), columns=user_columns)

    sql, params = create_users.to_sql()
    print("=== Create Users Table ===")
    print(f"SQL: {sql}")
    print(f"Params: {params}")
    print()

    # Execute DDL
    backend.execute(sql, params)

    # Introspection: Verify table was created
    print_table_list(introspector, "After creating users table")
    print_table_info(introspector, "users", "users table structure")

    # ============================================================
    # Example 2: Create table with IF NOT EXISTS
    # ============================================================
    create_products = CreateTableStatement(
        dialect,
        Table(dialect, "products"),
        columns=[
            ColumnDefinition(
                dialect,
                "id",
                IntegerType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect))],
            ),
            ColumnDefinition(dialect, "name", VarCharType(dialect, length=100)),
            ColumnDefinition(
                dialect,
                "price",
                FloatType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))],
            ),
        ],
        if_not_exists=True,
    )

    sql, params = create_products.to_sql()
    print("=== Create Products Table (IF NOT EXISTS) ===")
    print(f"SQL: {sql}")
    print()

    # Execute DDL
    backend.execute(sql, params)

    # Introspection: Verify products table was created
    print_table_list(introspector, "After creating products table")
    print_table_info(introspector, "products", "products table structure")

    # ============================================================
    # Example 3: Create temporary table
    # ============================================================
    create_temp = CreateTableStatement(
        dialect,
        Table(dialect, "temp_sessions"),
        columns=[
            ColumnDefinition(dialect, "session_id", VarCharType(dialect, length=50)),
            ColumnDefinition(dialect, "data", TextType(dialect)),
            ColumnDefinition(dialect, "expires_at", TimestampType(dialect)),
        ],
        temporary=True,
    )

    sql, params = create_temp.to_sql()
    print("=== Create Temporary Table ===")
    print(f"SQL: {sql}")
    print()

    # Execute DDL
    backend.execute(sql, params)

    # Introspection: Temporary tables are also visible in table_list
    print_table_list(introspector, "After creating temp table")

    # ============================================================
    # Example 4: Drop table
    # ============================================================
    # First create a table to drop
    create_to_drop = CreateTableStatement(
        dialect,
        Table(dialect, "old_table"),
        columns=[ColumnDefinition(dialect, "id", IntegerType(dialect))],
    )
    sql, params = create_to_drop.to_sql()
    backend.execute(sql, params)

    print("--- Before drop ---")
    tables = introspector.list_tables()
    print(f"Tables: {[t.name for t in tables]}")

    drop_old = DropTableStatement(dialect, Table(dialect, "old_table"), if_exists=True)

    sql, params = drop_old.to_sql()
    print("\n=== Drop Table ===")
    print(f"SQL: {sql}")
    print()

    # Execute DDL
    backend.execute(sql, params)

    # Introspection: Verify table was dropped
    print("--- After drop ---")
    tables = introspector.list_tables()
    print(f"Tables: {[t.name for t in tables]}")
    print()

    # ============================================================
    # Example 5: Alter table - Add column
    # ============================================================
    alter_add = AlterTableStatement(
        dialect,
        Table(dialect, "users"),
        actions=[
            AddColumnAction(
                dialect,
                ColumnDefinition(dialect, "phone", VarCharType(dialect, length=20)),
            )
        ],
    )

    sql, params = alter_add.to_sql()
    print("=== Alter Table - Add Column ===")
    print(f"SQL: {sql}")
    print()

    # Execute DDL
    backend.execute(sql, params)

    # Introspection: Verify column was added
    print_table_info(introspector, "users", "users table after adding phone column")

    # ============================================================
    # Example 6: Alter table - Drop column
    # ============================================================
    # First add a column to drop
    alter_add_field = AlterTableStatement(
        dialect,
        Table(dialect, "users"),
        actions=[
            AddColumnAction(
                dialect,
                ColumnDefinition(dialect, "temp_field", TextType(dialect)),
            )
        ],
    )
    sql, params = alter_add_field.to_sql()
    backend.execute(sql, params)

    print("--- Before dropping temp_field ---")
    print_table_info(introspector, "users", "users table before dropping temp_field")

    alter_drop = AlterTableStatement(
        dialect,
        Table(dialect, "users"),
        actions=[DropColumnAction(dialect, "temp_field")],
    )

    sql, params = alter_drop.to_sql()
    print("=== Alter Table - Drop Column ===")
    print(f"SQL: {sql}")
    print()

    # Execute DDL
    backend.execute(sql, params)

    # Introspection: Verify column was dropped
    print_table_info(introspector, "users", "users table after dropping temp_field")

    print("=== All DDL operations completed successfully! ===")
    print()
    print("NOTE: This example uses SQLite backend. Different backends (MySQL, PostgreSQL, etc.)")
    print("may have different introspection APIs and DDL support. Refer to specific backend documentation.")


if __name__ == "__main__":
    main()
