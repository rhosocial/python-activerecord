"""
Schema diff: detect removed and added indexes between two snapshots.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.expression import (
    CreateTableExpression, CreateIndexExpression,
    DropIndexExpression, ColumnDefinition,
    ColumnConstraint, ColumnConstraintType,
)
from rhosocial.activerecord.backend.expression.types import (
    IntegerType, TextType, FloatType,
)

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
backend.introspect_and_adapt()
dialect = backend.dialect

expr = CreateTableExpression(
    dialect=dialect, table="products", columns=[
        ColumnDefinition("id", IntegerType(),
            constraints=[ColumnConstraint(constraint_type=ColumnConstraintType.PRIMARY_KEY)]),
        ColumnDefinition("name", TextType()),
        ColumnDefinition("price", FloatType()),
    ]
)
sql, params = expr.to_sql()
backend.execute(sql, params)

expr = CreateIndexExpression(dialect, "idx_name", "products", ["name"])
sql, params = expr.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.schema import (  # noqa: E402
    SyncSchemaSnapshotBuilder,
)
from rhosocial.activerecord.backend.impl.sqlite.schema.differ import (  # noqa: E402
    SQLiteSchemaDiffer,
)

builder = SyncSchemaSnapshotBuilder(backend.introspector, dialect)
snapshot_before = builder.build(schema="main")

# Drop one index, add another
expr = DropIndexExpression(dialect, "idx_name", "products")
sql, params = expr.to_sql()
backend.execute(sql, params)
expr = CreateIndexExpression(dialect, "idx_price", "products", ["price"])
sql, params = expr.to_sql()
backend.execute(sql, params)

snapshot_after = builder.build(schema="main")

differ = SQLiteSchemaDiffer()
diff = differ.compare(snapshot_before, snapshot_after)

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
print(f"Modified tables: {diff.modified_tables}")

if "products" in diff.table_diffs:
    td = diff.table_diffs["products"]
    print(f"  Removed indexes: {[idx.name for idx in td.removed_indexes]}")
    print(f"  Added indexes:   {[idx.name for idx in td.added_indexes]}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()