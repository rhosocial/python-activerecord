"""
Chapter 3: Modeling Data - DDL Examples
Demonstrates DDL operations using expression-based API:
1. Create table with various column types and constraints
2. Create table with IF NOT EXISTS
3. Create temporary table
4. Drop table
5. Alter table operations
6. Introspection to verify schema changes
"""

from typing import ClassVar
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.expression import (
    ColumnDefinition,
    CreateTableExpression,
    DropTableExpression,
    AlterTableExpression,
    AddColumn,
    DropColumn,
)
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnConstraintType,
)


class User(ActiveRecord):
    """User Model for DDL demo"""
    username: str = Field(..., max_length=50)
    email: str
    is_active: bool = True

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return "users"


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
            print(f"  Column: {col.name}, Type: {col.data_type}, "
                  f"Nullable: {col.nullable}, PK: {col.is_primary_key}")
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
            "id",
            "INTEGER",
            constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]
        ),
        ColumnDefinition(
            "username",
            "VARCHAR(50)",
            constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]
        ),
        ColumnDefinition(
            "email",
            "VARCHAR(100)",
            constraints=[
                ColumnConstraint(ColumnConstraintType.NOT_NULL),
                ColumnConstraint(ColumnConstraintType.UNIQUE)
            ]
        ),
        ColumnDefinition("is_active", "BOOLEAN"),
        ColumnDefinition("created_at", "TIMESTAMP")
    ]

    create_users = CreateTableExpression(
        dialect=dialect,
        table_name="users",
        columns=user_columns
    )

    sql, params = create_users.to_sql()
    print("=== Create Users Table ===")
    print(f"SQL: {sql}")
    print(f"Params: {params}")
    print()

    # Execute DDL - convert to SQL string first
    sql_str, params_str = create_users.to_sql()
    backend.execute(sql_str, params_str)

    # Introspection: Verify table was created
    print_table_list(introspector, "After creating users table")
    print_table_info(introspector, "users", "users table structure")

    # ============================================================
    # Example 2: Create table with IF NOT EXISTS
    # ============================================================
    create_products = CreateTableExpression(
        dialect=dialect,
        table_name="products",
        columns=[
            ColumnDefinition(
                "id",
                "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]
            ),
            ColumnDefinition("name", "VARCHAR(100)"),
            ColumnDefinition("price", "REAL", constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)])
        ],
        if_not_exists=True
    )

    sql, params = create_products.to_sql()
    print("=== Create Products Table (IF NOT EXISTS) ===")
    print(f"SQL: {sql}")
    print()

    # Execute DDL
    sql_str, params_str = create_products.to_sql()
    backend.execute(sql_str, params_str)

    # Introspection: Verify products table was created
    print_table_list(introspector, "After creating products table")
    print_table_info(introspector, "products", "products table structure")

    # ============================================================
    # Example 3: Create temporary table
    # ============================================================
    create_temp = CreateTableExpression(
        dialect=dialect,
        table_name="temp_sessions",
        columns=[
            ColumnDefinition("session_id", "VARCHAR(50)"),
            ColumnDefinition("data", "TEXT"),
            ColumnDefinition("expires_at", "TIMESTAMP")
        ],
        temporary=True
    )

    sql, params = create_temp.to_sql()
    print("=== Create Temporary Table ===")
    print(f"SQL: {sql}")
    print()

    # Execute DDL
    sql_str, params_str = create_temp.to_sql()
    backend.execute(sql_str, params_str)

    # Introspection: Temporary tables are also visible in table_list
    print_table_list(introspector, "After creating temp table")

    # ============================================================
    # Example 4: Drop table
    # ============================================================
    # First create a table to drop
    create_to_drop = CreateTableExpression(
        dialect=dialect,
        table_name="old_table",
        columns=[ColumnDefinition("id", "INTEGER")]
    )
    sql_str, params_str = create_to_drop.to_sql()
    backend.execute(sql_str, params_str)

    print("--- Before drop ---")
    tables = introspector.list_tables()
    print(f"Tables: {[t.name for t in tables]}")

    drop_old = DropTableExpression(
        dialect,
        table_name="old_table",
        if_exists=True
    )

    sql, params = drop_old.to_sql()
    print("\n=== Drop Table ===")
    print(f"SQL: {sql}")
    print()

    # Execute DDL
    sql_str, params_str = drop_old.to_sql()
    backend.execute(sql_str, params_str)

    # Introspection: Verify table was dropped
    print("--- After drop ---")
    tables = introspector.list_tables()
    print(f"Tables: {[t.name for t in tables]}")
    print()

    # ============================================================
    # Example 5: Alter table - Add column
    # ============================================================
    alter_add = AlterTableExpression(
        dialect,
        table_name="users",
        actions=[
            AddColumn(
                ColumnDefinition(
                    "phone",
                    "VARCHAR(20)"
                )
            )
        ]
    )

    sql, params = alter_add.to_sql()
    print("=== Alter Table - Add Column ===")
    print(f"SQL: {sql}")
    print()

    # Execute DDL
    sql_str, params_str = alter_add.to_sql()
    backend.execute(sql_str, params_str)

    # Introspection: Verify column was added
    print_table_info(introspector, "users", "users table after adding phone column")

    # ============================================================
    # Example 6: Alter table - Drop column
    # ============================================================
    # First add a column to drop
    alter_add_field = AlterTableExpression(
        dialect,
        table_name="users",
        actions=[
            AddColumn(ColumnDefinition("temp_field", "TEXT"))
        ]
    )
    sql_str, params_str = alter_add_field.to_sql()
    backend.execute(sql_str, params_str)

    print("--- Before dropping temp_field ---")
    print_table_info(introspector, "users", "users table before dropping temp_field")

    alter_drop = AlterTableExpression(
        dialect,
        table_name="users",
        actions=[
            DropColumn("temp_field")
        ]
    )

    sql, params = alter_drop.to_sql()
    print("=== Alter Table - Drop Column ===")
    print(f"SQL: {sql}")
    print()

    # Execute DDL
    sql_str, params_str = alter_drop.to_sql()
    backend.execute(sql_str, params_str)

    # Introspection: Verify column was dropped
    print_table_info(introspector, "users", "users table after dropping temp_field")

    print("=== All DDL operations completed successfully! ===")
    print()
    print("NOTE: This example uses SQLite backend. Different backends (MySQL, PostgreSQL, etc.)")
    print("may have different introspection APIs and DDL support. Refer to specific backend documentation.")


if __name__ == "__main__":
    main()