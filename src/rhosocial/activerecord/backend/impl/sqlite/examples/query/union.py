"""
UNION using SetOperationExpression - SQLite.

This example demonstrates:
1. UNION (distinct)
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType
2. UNION ALL
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect

from rhosocial.activerecord.backend.expression import (  # noqa: E402
    CreateTableExpression,
    InsertExpression,
    ValuesSource,
    DropTableExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal, Column  # noqa: E402
from rhosocial.activerecord.backend.expression.statements import (  # noqa: E402
    ColumnDefinition,
)

create_table = CreateTableExpression(
    dialect=dialect,
    table=Table(dialect, 'users'),
    columns=[
        ColumnDefinition(dialect, "id", IntegerType()),
        ColumnDefinition(dialect, "name", TextType()),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
print(f"Create table SQL: {sql}")
backend.execute(sql, params)

insert = InsertExpression(
    dialect=dialect,
    into=Table(dialect, 'users'),
    columns=["id", "name"],
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, 1), Literal(dialect, "Alice")],
            [Literal(dialect, 2), Literal(dialect, "Bob")],
        ],
    ),
)
sql, params = insert.to_sql()
print(f"Insert SQL: {sql}")
backend.execute(sql, params)

# ============================================================
# SECTION: UNION (using SetOperationExpression)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    SetOperationExpression,
)
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from .....expression.objects import Table

# First query
query1 = QueryExpression(
    dialect=dialect,
    select=[Column(dialect, "name")],
    from_=NamedRelationRef(dialect, Table(dialect, "users")),
)

query2 = QueryExpression(
    dialect=dialect,
    select=[Literal(dialect, "Charlie")],
)

# Union
union_expr = SetOperationExpression(
    dialect=dialect,
    left=query1,
    operation="UNION",
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
    operation="UNION",
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
drop_expr = DropTableExpression(dialect=dialect, table=Table(dialect, 'users'), if_exists=True)
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
