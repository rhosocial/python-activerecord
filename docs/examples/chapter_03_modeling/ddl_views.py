"""Chapter 3: Modeling Data - DDL Views Examples

Demonstrates DDL operations for views:
1. Create basic view
2. Create view with column aliases
3. Create view with OR REPLACE
4. Drop view
5. Introspection to verify view creation
"""

from typing import ClassVar

from rhosocial.activerecord.backend.expression import (
    Column,
    ColumnDefinition,
    NamedRelationRef,
    QueryStatement,
)
from rhosocial.activerecord.backend.expression.objects import Table, View
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
    CreateTableStatement,
    CreateViewStatement,
    DropViewStatement,
)
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.model import ActiveRecord


class User(ActiveRecord):
    """User Model for DDL view demo"""

    __table_name__ = "users"

    id: int = None
    name: str
    email: str
    status: str = "active"

    c: ClassVar[FieldProxy] = FieldProxy()


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
            dialect, "id", IntegerType(dialect),
            constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect))]
        ),
        ColumnDefinition(
            dialect, "name", VarCharType(dialect, length=100),
            constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]
        ),
        ColumnDefinition(
            dialect, "email", VarCharType(dialect, length=255),
            constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]
        ),
        ColumnDefinition(dialect, "status", VarCharType(dialect, length=20)),
    ]

    create_users = CreateTableStatement(dialect, Table(dialect, "users"), columns=user_columns)
    sql_str, params = create_users.to_sql()
    backend.execute(sql_str, params)
    print("Users table created.")

    # Insert some sample data
    backend.execute("INSERT INTO users (id, name, email, status) VALUES (1, 'Alice', 'alice@example.com', 'active')")
    backend.execute("INSERT INTO users (id, name, email, status) VALUES (2, 'Bob', 'bob@example.com', 'inactive')")
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
    all_users_query = QueryStatement(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "name"), Column(dialect, "email")],
        from_=NamedRelationRef(dialect, Table(dialect, "users")),
    )

    create_all_users_view = CreateViewStatement(
        dialect, View(dialect, "all_users"), query=all_users_query
    )

    sql, params = create_all_users_view.to_sql()
    print("=== Create Basic View ===")
    print(f"SQL: {sql}")
    print()

    sql_str, params = create_all_users_view.to_sql()
    backend.execute(sql_str, params)

    # Introspection: Verify view was created
    print("--- Views after creation ---")
    views = introspector.list_views()
    for v in views:
        print(f"  View: {v.name}")

    # Query the view
    print()
    print("--- Querying the view ---")
    for row in backend.fetch_all("SELECT * FROM all_users"):
        print(f"  {row}")
    print()

    # ============================================================
    # Example 2: Create view with column aliases
    # ============================================================
    user_details_query = QueryStatement(
        dialect,
        select=[
            Column(dialect, "id"),
            Column(dialect, "name"),
            Column(dialect, "email"),
            Column(dialect, "status"),
        ],
        from_=NamedRelationRef(dialect, Table(dialect, "users")),
    )

    create_aliased_view = CreateViewStatement(
        dialect,
        View(dialect, "user_details"),
        query=user_details_query,
        column_aliases=["user_id", "full_name", "contact_email", "user_status"],
    )

    sql, params = create_aliased_view.to_sql()
    print("=== Create View with Column Aliases ===")
    print(f"SQL: {sql}")
    print()

    sql_str, params = create_aliased_view.to_sql()
    backend.execute(sql_str, params)

    # Query the view
    print("--- Querying aliased view ---")
    for row in backend.fetch_all("SELECT * FROM user_details"):
        print(f"  {row}")
    print()

    # ============================================================
    # Example 3: Create view with OR REPLACE
    # ============================================================
    active_users_query = QueryStatement(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "name")],
        from_=NamedRelationRef(dialect, Table(dialect, "users")),
    )

    create_replace_view = CreateViewStatement(
        dialect, View(dialect, "active_users"), query=active_users_query, replace=True
    )

    sql, params = create_replace_view.to_sql()
    print("=== Create View with OR REPLACE ===")
    print(f"SQL: {sql}")
    print("Note: SQLite has no CREATE OR REPLACE VIEW; its dialect renders IF NOT EXISTS instead.")
    print()

    sql_str, params = create_replace_view.to_sql()
    backend.execute(sql_str, params)

    # Query the replaced view
    print("--- Querying replaced view ---")
    for row in backend.fetch_all("SELECT * FROM active_users"):
        print(f"  {row}")
    print()

    # ============================================================
    # Example 4: Drop view
    # ============================================================
    drop_view = DropViewStatement(dialect, View(dialect, "user_details"), if_exists=True)

    sql, params = drop_view.to_sql()
    print("=== Drop View ===")
    print(f"SQL: {sql}")
    print()

    sql_str, params = drop_view.to_sql()
    backend.execute(sql_str, params)

    # Introspection: Verify view was dropped
    print("--- Views after drop ---")
    introspector.clear_cache()
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
