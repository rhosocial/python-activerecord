"""
Chapter 3: Modeling Data - DDL Views Examples
Demonstrates DDL operations for views:
1. Create basic view
2. Create view with column aliases
3. Create view with OR REPLACE
4. Drop view
5. Introspection to verify view creation
"""

from typing import ClassVar
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.expression import (
    ColumnDefinition,
    CreateTableExpression,
    CreateViewExpression,
    DropViewExpression,
    QueryExpression,
    TableExpression,
    Column,
    Literal,
)
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnConstraintType,
)


class User(ActiveRecord):
    """User Model for DDL view demo"""
    name: str
    email: str
    status: str = "active"

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return "users"


def main():
    # Configure Database
    config = SQLiteConnectionConfig(database=":memory:")
    User.configure(config, SQLiteBackend)

    # Get dialect from backend
    dialect = User.__backend__.dialect
    backend = User.__backend__
    introspector = backend.introspector

    # Create base table first
    user_columns = [
        ColumnDefinition(
            "id",
            "INTEGER",
            constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]
        ),
        ColumnDefinition(
            "name",
            "VARCHAR(100)",
            constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]
        ),
        ColumnDefinition(
            "email",
            "VARCHAR(255)",
            constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]
        ),
        ColumnDefinition("status", "VARCHAR(20)")
    ]

    create_users = CreateTableExpression(
        dialect=dialect,
        table_name="users",
        columns=user_columns
    )
    sql_str, params_str = create_users.to_sql()
    backend.execute(sql_str, params_str)
    print("Users table created.")

    # Insert some sample data
    backend.execute(
        "INSERT INTO users (id, name, email, status) VALUES (1, 'Alice', 'alice@example.com', 'active')"
    )
    backend.execute(
        "INSERT INTO users (id, name, email, status) VALUES (2, 'Bob', 'bob@example.com', 'inactive')"
    )
    backend.execute(
        "INSERT INTO users (id, name, email, status) VALUES (3, 'Charlie', 'charlie@example.com', 'active')"
    )
    print("Sample data inserted.")
    print()

    # ============================================================
    # Example 1: Create basic view
    # ============================================================
    # Note: SQLite doesn't allow parameters in VIEW definitions.
    # We use a simple SELECT without WHERE parameter.
    all_users_query = QueryExpression(
        dialect,
        select=[
            Column(dialect, "id"),
            Column(dialect, "name"),
            Column(dialect, "email")
        ],
        from_=TableExpression(dialect, "users")
    )

    create_active_view = CreateViewExpression(
        dialect,
        view_name="all_users",
        query=all_users_query
    )

    sql, params = create_active_view.to_sql()
    print("=== Create Basic View ===")
    print(f"SQL: {sql}")
    print()

    sql_str, params_str = create_active_view.to_sql()
    backend.execute(sql_str, params_str)

    # Introspection: Verify view was created
    print("--- Views after creation ---")
    views = introspector.list_views()
    for v in views:
        print(f"  View: {v.name}")

    # Query the view
    print()
    print("--- Querying the view ---")
    result = backend.execute("SELECT * FROM all_users")
    if result and result.data:
        for row in result.data:
            print(f"  {row}")
    print()

    # ============================================================
    # Example 2: Create view with column aliases
    # ============================================================
    user_details_query = QueryExpression(
        dialect,
        select=[
            Column(dialect, "id"),
            Column(dialect, "name"),
            Column(dialect, "email"),
            Column(dialect, "status")
        ],
        from_=TableExpression(dialect, "users")
    )

    create_aliased_view = CreateViewExpression(
        dialect,
        view_name="user_details",
        query=user_details_query,
        column_aliases=["user_id", "full_name", "contact_email", "user_status"]
    )

    sql, params = create_aliased_view.to_sql()
    print("=== Create View with Column Aliases ===")
    print(f"SQL: {sql}")
    print()

    sql_str, params_str = create_aliased_view.to_sql()
    backend.execute(sql_str, params_str)

    # Query the view
    print("--- Querying aliased view ---")
    result = backend.execute("SELECT * FROM user_details")
    if result and result.data:
        for row in result.data:
            print(f"  {row}")
    print()

    # ============================================================
    # Example 3: Create view with OR REPLACE
    # ============================================================
    all_users_query = QueryExpression(
        dialect,
        select=[
            Column(dialect, "id"),
            Column(dialect, "name")
        ],
        from_=TableExpression(dialect, "users")
    )

    create_replace_view = CreateViewExpression(
        dialect,
        view_name="active_users",
        query=all_users_query,
        replace=True
    )

    sql, params = create_replace_view.to_sql()
    print("=== Create View with OR REPLACE ===")
    print(f"SQL: {sql}")
    print()

    sql_str, params_str = create_replace_view.to_sql()
    backend.execute(sql_str, params_str)

    # Query the replaced view
    print("--- Querying replaced view ---")
    result = backend.execute("SELECT * FROM active_users")
    if result and result.data:
        for row in result.data:
            print(f"  {row}")
    print()

    # ============================================================
    # Example 4: Drop view
    # ============================================================
    drop_view = DropViewExpression(
        dialect,
        view_name="user_details",
        if_exists=True
    )

    sql, params = drop_view.to_sql()
    print("=== Drop View ===")
    print(f"SQL: {sql}")
    print()

    sql_str, params_str = drop_view.to_sql()
    backend.execute(sql_str, params_str)

    # Introspection: Verify view was dropped
    print("--- Views after drop ---")
    views = introspector.list_views()
    for v in views:
        print(f"  View: {v.name}")
    if not views:
        print("  (no views)")
    print()

    print("=== All view DDL operations completed successfully! ===")
    print()
    print("NOTE: This example uses SQLite backend. Different backends (MySQL, PostgreSQL, etc.)")
    print("may have different view support (e.g., materialized views, view algorithms).")


if __name__ == "__main__":
    main()