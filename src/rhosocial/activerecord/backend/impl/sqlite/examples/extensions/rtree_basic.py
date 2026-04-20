"""
R-Tree spatial index operations.

This example demonstrates how to create and query an R-Tree virtual table
for efficient spatial indexing of geographic coordinates.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
dialect = backend.dialect

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite.extension.extensions.rtree import RTreeExtension
from rhosocial.activerecord.backend.expression import (
    Column,
    InsertExpression,
    ValuesSource,
    QueryExpression,
    TableExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal

# Get R-Tree extension
rtree = RTreeExtension()

# Create R-Tree virtual table for 2D coordinates (longitude, latitude)
create_sql, create_params = rtree.format_create_virtual_table(
    table_name='locations',
    dimensions=2,
)

# Execute CREATE VIRTUAL TABLE
backend.execute(create_sql, create_params)
print(f"Created R-Tree table: {create_sql}")

# Insert spatial data using InsertExpression
# R-Tree table expects: rowid, min0, max0, min1, max1 (for 2 dimensions)
insert_expr = InsertExpression(
    dialect=dialect,
    into='locations',
    columns=['min0', 'max0', 'min1', 'max1'],
    source=ValuesSource(dialect, [[
        Literal(dialect, -122.4194),
        Literal(dialect, -122.4194),
        Literal(dialect, 37.7749),
        Literal(dialect, 37.7749),
    ]]),
)
sql, params = insert_expr.to_sql()
backend.execute(sql, params)

insert_expr2 = InsertExpression(
    dialect=dialect,
    into='locations',
    columns=['min0', 'max0', 'min1', 'max1'],
    source=ValuesSource(dialect, [[
        Literal(dialect, -122.0),
        Literal(dialect, -121.0),
        Literal(dialect, 37.0),
        Literal(dialect, 38.0),
    ]]),
)
sql, params = insert_expr2.to_sql()
backend.execute(sql, params)

# Query using range filter with QueryExpression
# R-Tree columns: rowid, min0, max0, min1, max1 (for 2 dimensions)
col_rowid = Column(dialect, 'rowid', table='locations')
col_min0 = Column(dialect, 'min0', table='locations')
col_max0 = Column(dialect, 'max0', table='locations')
col_min1 = Column(dialect, 'min1', table='locations')
col_max1 = Column(dialect, 'max1', table='locations')

predicate = (col_min0 >= Literal(dialect, -122.5)) & (col_max0 <= Literal(dialect, -121.5))
predicate = predicate & (col_min1 >= Literal(dialect, 37.5)) & (col_max1 <= Literal(dialect, 38.5))

range_query = QueryExpression(
    dialect=dialect,
    select=[col_rowid, col_min0, col_max0, col_min1, col_max1],
    from_=TableExpression(dialect, 'locations'),
    where=predicate,
)

sql, params = range_query.to_sql()
print(f"\nRange query SQL: {sql}")
print(f"Params: {params}")

options = ExecutionOptions(stmt_type=StatementType.DQL)
result = backend.execute(sql, params, options=options)
print(f"Results: {len(result.data) if result.data else 0} rows")
for row in result.data or []:
    print(f"  {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()