"""
CREATE VIEW - SQLite.

This example demonstrates:
1. CREATE VIEW
2. CREATE OR REPLACE VIEW
3. Drop view
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
# SECTION: CREATE VIEW
# ============================================================
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    TableExpression,
    CreateViewExpression,
    DropViewExpression,
)

query = QueryExpression(
    dialect=dialect,
    select=[Column(dialect, 'name')],
    from_=TableExpression(dialect, 'users'),
)

view_expr = CreateViewExpression(
    dialect=dialect,
    view_name='user_names',
    query=query,
)
sql, params = view_expr.to_sql()
print(f"CREATE VIEW SQL: {sql}")
print(f"Params: {params}")

options = ExecutionOptions(stmt_type=StatementType.DDL)
backend.execute(sql, params, options=options)

# Query the view
view_query = QueryExpression(
    dialect=dialect,
    select=[Column(dialect, 'name')],
    from_=TableExpression(dialect, 'user_names'),
)
sql, params = view_query.to_sql()
result = backend.execute(
    sql,
    params,
    options=ExecutionOptions(stmt_type=StatementType.DQL),
)
print(f"View result: {result.data}")

# ============================================================
# SECTION: CREATE OR REPLACE VIEW
# ============================================================
view_expr_replace = CreateViewExpression(
    dialect=dialect,
    view_name='user_names',
    query=query,
    replace=True,
)
sql, params = view_expr_replace.to_sql()
print(f"CREATE OR REPLACE VIEW SQL: {sql}")
backend.execute(sql, params, options=options)

# ============================================================
# SECTION: DROP VIEW
# ============================================================
drop_view = DropViewExpression(
    dialect=dialect,
    view_name='user_names',
)
sql, params = drop_view.to_sql()
print(f"DROP VIEW SQL: {sql}")
backend.execute(sql, params, options=options)

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
# 1. Use CreateViewExpression to create views
# 2. Use replace=True to replace existing view
# 3. Use DropViewExpression to drop views
