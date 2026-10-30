from rhosocial.activerecord.backend.expression.statements import (
    ColumnPrimaryKeyConstraint,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.impl.sqlite.schema.differ import (  # noqa: E402
    SQLiteSchemaDiffer,
)
from rhosocial.activerecord.backend.schema import (  # noqa: E402
    SyncSchemaSnapshotBuilder,
)
from rhosocial.activerecord.backend.expression.types import (
    IntegerType, TextType, FloatType,
)
from rhosocial.activerecord.backend.expression import (
    CreateTableStatement,
    CreateIndexStatement,
    DropIndexStatement,
    ColumnDefinition,
    ColumnConstraint,
)
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
"""
Schema diff: detect removed and added indexes between two snapshots.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
backend.introspect_and_adapt()
dialect = backend.dialect

expr = CreateTableStatement(
    dialect=dialect, table=Table(dialect, 'products'), columns=[
        ColumnDefinition(dialect, "id", IntegerType(),
            constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect))]),
        ColumnDefinition(dialect, "name", TextType()),
        ColumnDefinition(dialect, "price", FloatType()),
    ]
)
sql, params = expr.to_sql()
backend.execute(sql, params)

expr = CreateIndexStatement(dialect, "idx_name", "products", ["name"])
sql, params = expr.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================

builder = SyncSchemaSnapshotBuilder(backend.introspector, dialect)
snapshot_before = builder.build(schema="main")

# Drop one index, add another
expr = DropIndexStatement(dialect, "idx_name", "products")
sql, params = expr.to_sql()
backend.execute(sql, params)
expr = CreateIndexStatement(dialect, "idx_price", "products", ["price"])
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