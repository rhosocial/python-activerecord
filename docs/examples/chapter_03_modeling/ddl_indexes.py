"""
Chapter 3: Modeling Data - DDL with Indexes
Demonstrates index creation and management:
1. Create basic index
2. Create unique index
3. Create composite index
4. Create partial index (with WHERE clause)
5. Drop index
"""

from typing import ClassVar
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.expression import (
    ColumnDefinition,
    CreateTableExpression,
    Column,
    Literal,
    CreateIndexExpression,
    DropIndexExpression,
)
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnConstraintType,
)


class Product(ActiveRecord):
    """Product Model for DDL index demo"""
    name: str
    category: str
    price: float
    status: str = "active"

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return "products"


def main():
    # Configure Database
    config = SQLiteConnectionConfig(database=":memory:")
    Product.configure(config, SQLiteBackend)

    # Get dialect from backend
    dialect = Product.__backend__.dialect
    backend = Product.__backend__

    # First create the products table
    product_columns = [
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
        ColumnDefinition("category", "VARCHAR(50)"),
        ColumnDefinition("price", "REAL"),
        ColumnDefinition("status", "VARCHAR(20)")
    ]

    create_products = CreateTableExpression(
        dialect=dialect,
        table_name="products",
        columns=product_columns
    )

    sql_str, params_str = create_products.to_sql()
    backend.execute(sql_str, params_str)
    print("Products table created.")

    # ============================================================
    # Example 1: Create basic index
    # ============================================================
    create_idx = CreateIndexExpression(
        dialect,
        index_name="idx_products_name",
        table_name="products",
        columns=["name"]
    )

    sql, params = create_idx.to_sql()
    print("=== Create Basic Index ===")
    print(f"SQL: {sql}")
    print()

    sql_str, params_str = create_idx.to_sql()
    backend.execute(sql_str, params_str)

    # ============================================================
    # Example 2: Create unique index
    # ============================================================
    create_unique_idx = CreateIndexExpression(
        dialect,
        index_name="idx_products_category_name",
        table_name="products",
        columns=["category", "name"],
        unique=True
    )

    sql, params = create_unique_idx.to_sql()
    print("=== Create Unique Composite Index ===")
    print(f"SQL: {sql}")
    print()

    sql_str, params_str = create_unique_idx.to_sql()
    backend.execute(sql_str, params_str)

    # ============================================================
    # Example 3: Create partial index (with WHERE clause)
    # ============================================================
    create_partial_idx = CreateIndexExpression(
        dialect,
        index_name="idx_products_active_price",
        table_name="products",
        columns=["price"],
        where=Column(dialect, "status") == Literal(dialect, "active")
    )

    sql, params = create_partial_idx.to_sql()
    print("=== Create Partial Index (with WHERE) ===")
    print(f"SQL: {sql}")
    print(f"Params: {params}")
    print()

    # Note: SQLite partial indexes require literals in WHERE clause, not parameters.
    # This will fail when executed via parameterized query.
    # For demonstration, we skip execution but show the generated SQL.
    # sql_str, params_str = create_partial_idx.to_sql()
    # backend.execute(sql_str, params_str)
    print("Note: SQLite partial indexes don't support parameters in WHERE clause.")
    print("The generated SQL shows how it would look with a literal value.")
    print()

    # Note: SQLite doesn't support USING BTREE syntax, so this would fail.
    # Showing it for demonstration purposes only.
    print("=== Index Type (not supported in SQLite) ===")
    create_btree_idx = CreateIndexExpression(
        dialect,
        index_name="idx_products_category",
        table_name="products",
        columns=["category"],
        index_type="BTREE"
    )
    sql, params = create_btree_idx.to_sql()
    print(f"SQL: {sql}")
    print("Note: SQLite doesn't support index_type (USING BTREE).")
    print()

    # ============================================================
    # Example 5: Drop index
    # ============================================================
    drop_idx = DropIndexExpression(
        dialect,
        index_name="idx_products_category",
        if_exists=True
    )

    sql, params = drop_idx.to_sql()
    print("=== Drop Index ===")
    print(f"SQL: {sql}")
    print()

    sql_str, params_str = drop_idx.to_sql()
    backend.execute(sql_str, params_str)

    # Introspection: Verify index was dropped
    print("--- Indexes on products table after drop ---")
    indexes = backend.introspector.list_indexes("products")
    for idx in indexes:
        print(f"  Index: {idx.name}, Unique: {idx.is_unique}")
    if not indexes:
        print("  (none)")

    print()
    print("=== All index DDL operations completed successfully! ===")
    print()
    print("NOTE: This example uses SQLite backend. Different backends (MySQL, PostgreSQL, etc.)")
    print("may have different introspection APIs and DDL support. Refer to specific backend documentation.")


if __name__ == "__main__":
    main()