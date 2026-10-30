"""Chapter 3: Modeling Data - DDL with Indexes

Demonstrates index creation and management:
1. Create basic index
2. Create unique index
3. Create composite index
4. Create partial index (with WHERE clause)
5. Drop index
"""

from typing import ClassVar

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import (
    ColumnDefinition,
    Literal,
    StringColumn,
)
from rhosocial.activerecord.backend.expression.objects import Index, Table
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
    CreateIndexStatement,
    CreateTableStatement,
    DropIndexStatement,
)
from rhosocial.activerecord.backend.expression.types import FloatType, IntegerType, VarCharType
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.model import ActiveRecord


class Product(ActiveRecord):
    """Product Model for DDL index demo"""

    __table_name__ = "products"

    id: int = None
    name: str
    category: str
    price: float
    status: str = "active"

    c: ClassVar[FieldProxy] = FieldProxy()


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
            dialect, "id", IntegerType(dialect),
            constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect))]
        ),
        ColumnDefinition(
            dialect, "name", VarCharType(dialect, length=100),
            constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]
        ),
        ColumnDefinition(dialect, "category", VarCharType(dialect, length=50)),
        ColumnDefinition(dialect, "price", FloatType(dialect)),
        ColumnDefinition(dialect, "status", VarCharType(dialect, length=20)),
    ]

    create_products = CreateTableStatement(
        dialect, Table(dialect, "products"), columns=product_columns
    )

    sql_str, params = create_products.to_sql()
    backend.execute(sql_str, params)
    print("Products table created.")

    # ============================================================
    # Example 1: Create basic index
    # ============================================================
    create_idx = CreateIndexStatement(
        dialect, Index(dialect, "idx_products_name"), Table(dialect, "products"), columns=["name"]
    )

    sql, params = create_idx.to_sql()
    print("=== Create Basic Index ===")
    print(f"SQL: {sql}")
    print()

    sql_str, params = create_idx.to_sql()
    backend.execute(sql_str, params)

    # ============================================================
    # Example 2: Create unique composite index
    # ============================================================
    create_unique_idx = CreateIndexStatement(
        dialect,
        Index(dialect, "idx_products_category_name"),
        Table(dialect, "products"),
        columns=["category", "name"],
        unique=True,
    )

    sql, params = create_unique_idx.to_sql()
    print("=== Create Unique Composite Index ===")
    print(f"SQL: {sql}")
    print()

    sql_str, params = create_unique_idx.to_sql()
    backend.execute(sql_str, params)

    # ============================================================
    # Example 3: Create partial index (with WHERE clause)
    # ============================================================
    # The predicate is built by a typed column; the literal is marked
    # inline because SQLite partial indexes cannot carry bind parameters.
    create_partial_idx = CreateIndexStatement(
        dialect,
        Index(dialect, "idx_products_active_price"),
        Table(dialect, "products"),
        columns=["price"],
        where=StringColumn(dialect, "status") == Literal(dialect, "active", inline=True),
    )

    sql, params = create_partial_idx.to_sql()
    print("=== Create Partial Index (with WHERE) ===")
    print(f"SQL: {sql}")
    print(f"Params: {params}")
    print()

    sql_str, params = create_partial_idx.to_sql()
    backend.execute(sql_str, params)

    # ============================================================
    # Example 4: Index type (not supported in SQLite)
    # ============================================================
    # SQLite doesn't support USING BTREE syntax, so the dialect refuses.
    print("=== Index Type (not supported in SQLite) ===")
    try:
        create_btree_idx = CreateIndexStatement(
            dialect,
            Index(dialect, "idx_products_category"),
            Table(dialect, "products"),
            columns=["category"],
            index_type="BTREE",
        )
        sql, params = create_btree_idx.to_sql()
        print(f"SQL: {sql}")
    except UnsupportedFeatureError as exc:
        print(f"Refused: {exc}")
    print()

    # ============================================================
    # Example 5: Drop index
    # ============================================================
    drop_idx = DropIndexStatement(
        dialect, Index(dialect, "idx_products_active_price"), if_exists=True
    )

    sql, params = drop_idx.to_sql()
    print("=== Drop Index ===")
    print(f"SQL: {sql}")
    print()

    sql_str, params = drop_idx.to_sql()
    backend.execute(sql_str, params)

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
