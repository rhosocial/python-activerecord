"""
Geopoly polygon geometry operations.

This example demonstrates how to use the Geopoly extension for
polygon area calculation and overlap detection.

NOTE: Geopoly requires SQLite 3.26.0+. Some functions may not be 
available in all SQLite versions.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
import sqlite3

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
dialect = backend.dialect

# Check SQLite version for geopoly support
sqlite_version = tuple(int(x) for x in sqlite3.sqlite_version.split('.'))
if sqlite_version < (3, 26, 0):
    print(f"Skipping Geopoly example: requires SQLite 3.26.0+, found {sqlite3.sqlite_version}")
    backend.disconnect()
    exit(0)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    Column,
    InsertExpression,
    ValuesSource,
    QueryExpression,
    TableExpression,
    FunctionCall,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.impl.sqlite.functions import geopoly_area

# Create Geopoly virtual table using dialect
create_sql, create_params = dialect.format_create_virtual_table(
    module='geopoly',
    table_name='polygons',
    columns=[],
)

try:
    backend.execute(create_sql, create_params)
    print(f"Created Geopoly table: {create_sql}")
except Exception as e:
    print(f"Error creating Geopoly table: {e}")
    backend.disconnect()
    exit(0)

# Check geopoly is available
extensions = dialect.detect_extensions()
if 'geopoly' not in extensions:
    print("Geopoly extension not available, skipping example")
    backend.disconnect()
    exit(0)

# Insert polygon data - GeoJSON format: [[x1,y1],[x2,y2],...,[first,last]]
# Must close the polygon (first point == last point)
polygon_json = '[[0,0],[1,0],[0.5,1],[0,0]]'
insert_expr = InsertExpression(
    dialect=dialect,
    into='polygons',
    columns=['_shape'],
    source=ValuesSource(dialect, [[
        Literal(dialect, polygon_json),
    ]]),
)
sql, params = insert_expr.to_sql()
try:
    backend.execute(sql, params)
    print(f"Inserted polygon: {polygon_json}")
except Exception as e:
    print(f"Error inserting polygon: {e}")
    backend.disconnect()
    exit(0)

# Query with area calculation using geopoly_area function
col_shape = Column(dialect, '_shape', table='polygons')
area_query = QueryExpression(
    dialect=dialect,
    select=[
        col_shape,
        geopoly_area(dialect, col_shape).as_('area'),
    ],
    from_=TableExpression(dialect, 'polygons'),
)

sql, params = area_query.to_sql()
print(f"\nArea query SQL: {sql}")
print(f"Params: {params}")

options = ExecutionOptions(stmt_type=StatementType.DQL)
result = backend.execute(sql, params, options=options)
print(f"Results: {len(result.data) if result.data else 0} rows")
for row in result.data or []:
    print(f"  {row}")

# Note: geopoly_contains may not be available in all SQLite versions
# If available, use: col.overlaps(point) or geopoly_overlap

print("\nNote: Some geopoly functions (geopoly_contains, geopoly_centerpoint) may not be available in all SQLite versions.")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()