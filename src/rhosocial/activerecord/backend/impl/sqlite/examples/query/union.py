"""
UNION using SetOperationExpression - SQLite.

This example demonstrates:
1. UNION (distinct)
2. UNION ALL
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

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    InsertExpression,
    ValuesSource,
    DropTableExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal, Column
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='users',
    columns=[
        ColumnDefinition('id', 'INT'),
        ColumnDefinition('name', 'TEXT'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
print(f"Create table SQL: {sql}")
backend.execute(sql, params)

insert = InsertExpression(
    dialect=dialect,
    into='users',
    columns=['id', 'name'],
    source=ValuesSource(dialect, [
        [Literal(dialect, 1), Literal(dialect, 'Alice')],
        [Literal(dialect, 2), Literal(dialect, 'Bob')],
    ]),
)
sql, params = insert.to_sql()
print(f"Insert SQL: {sql}")
backend.execute(sql, params)

# ============================================================
# SECTION: UNION (using SetOperationExpression)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    TableExpression,
    SetOperationExpression,
)

# First query
query1 = QueryExpression(
    dialect=dialect,
    select=[Column(dialect, 'name')],
    from_=TableExpression(dialect, 'users'),
)

query2 = QueryExpression(
    dialect=dialect,
    select=[Literal(dialect, 'Charlie')],
)

# Union
union_expr = SetOperationExpression(
    dialect=dialect,
    left=query1,
    operation='UNION',
    right=query2,
)
sql, params = union_expr.to_sql()
print(f"UNION SQL: {sql}")
print(f"Params: {params}")

options = ExecutionOptions(stmt_type=StatementType.DQL)
result = backend.execute(sql, params, options=options)
print(f"Result: {result.data}")

# ============================================================
# SECTION: UNION ALL
# ============================================================
union_all = SetOperationExpression(
    dialect=dialect,
    left=query1,
    operation='UNION',
    all_=True,
    right=query2,
)
sql, params = union_all.to_sql()
print(f"UNION ALL SQL: {sql}")
result = backend.execute(sql, params, options=options)
print(f"UNION ALL result: {result.data}")

# ============================================================
# SECTION: Teardown
# ============================================================
drop_expr = DropTableExpression(dialect=dialect, table_name='users', if_exists=True)
sql, params = drop_expr.to_sql()
backend.execute(sql, params)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Use SetOperationExpression with operation='UNION'
# 2. Use operation='UNION', all_=True for UNION ALL
# 3. UNION removes duplicates, UNION ALL keeps all
