"""
CREATE VIEW - SQLite.

This example demonstrates:
1. CREATE VIEW
2. CREATE OR REPLACE VIEW
3. Drop view
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect


# Version-gated features (RETURNING, JSON1, math functions) read the
# dialect version, which is only known after the server is inspected.
backend.introspect_and_adapt()
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
    table="users",
    columns=[
        ColumnDefinition(dialect, "id", IntegerType(dialect)),
        ColumnDefinition(dialect, "name", TextType(dialect)),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
print(f"Create table SQL: {sql}")
backend.execute(sql, params)

insert = InsertExpression(
    dialect=dialect,
    into="users",
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
# SECTION: CREATE VIEW
# ============================================================
from rhosocial.activerecord.backend.expression import (  # noqa: E402
    QueryExpression,
    TableExpression,
    CreateViewExpression,
    DropViewExpression,
)

query = QueryExpression(
    dialect=dialect,
    select=[Column(dialect, "name")],
    from_=TableExpression(dialect, "users"),
)

view_expr = CreateViewExpression(
    dialect=dialect,
    view_name="user_names",
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
    select=[Column(dialect, "name")],
    from_=TableExpression(dialect, "user_names"),
)
sql, params = view_query.to_sql()
result = backend.execute(
    sql,
    params,
    options=ExecutionOptions(stmt_type=StatementType.DQL),
)
print(f"View result: {result.data}")

# ============================================================
# SECTION: REPLACING A VIEW
# ============================================================
# SQLite has no CREATE OR REPLACE VIEW -- it rejects the OR REPLACE clause as a
# syntax error. Asking for replace=True here raises UnsupportedFeatureError
# rather than quietly emitting CREATE VIEW IF NOT EXISTS, which would leave the
# old definition in place and report success.
#
# Dialects that do support it (PostgreSQL, MySQL, ClickHouse) can use
# replace=True directly. On SQLite, drop first and then create:
drop_existing = DropViewExpression(
    dialect=dialect,
    view_name="user_names",
    if_exists=True,
)
sql, params = drop_existing.to_sql()
print(f"DROP VIEW IF EXISTS SQL: {sql}")
backend.execute(sql, params, options=options)

view_expr_recreated = CreateViewExpression(
    dialect=dialect,
    view_name="user_names",
    query=query,
)
sql, params = view_expr_recreated.to_sql()
print(f"CREATE VIEW SQL: {sql}")
backend.execute(sql, params, options=options)

# ============================================================
# SECTION: DROP VIEW
# ============================================================
drop_view = DropViewExpression(
    dialect=dialect,
    view_name="user_names",
)
sql, params = drop_view.to_sql()
print(f"DROP VIEW SQL: {sql}")
backend.execute(sql, params, options=options)

# ============================================================
# SECTION: Teardown
# ============================================================
drop_expr = DropTableExpression(dialect=dialect, table="users", if_exists=True)
sql, params = drop_expr.to_sql()
backend.execute(sql, params)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Use CreateViewExpression to create views
# 2. To change an existing view, check the capability: replace=True works on
#    dialects that support CREATE OR REPLACE VIEW, but SQLite requires
#    DropViewExpression(if_exists=True) followed by CreateViewExpression
# 3. Use DropViewExpression to drop views
