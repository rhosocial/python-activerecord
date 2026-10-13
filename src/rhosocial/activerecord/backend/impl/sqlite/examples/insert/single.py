from rhosocial.activerecord.backend.expression.statements import (
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
)
from .....expression.objects import Table
from rhosocial.activerecord.backend.expression import InsertStatement, ValuesSource
from rhosocial.activerecord.backend.expression.statements import ColumnDefinition, ColumnConstraint
from rhosocial.activerecord.backend.expression.core import Literal, Wildcard
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.expression import (
    CreateTableStatement,
    DropTableStatement,
    QueryStatement,
)
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
"""
Single Row INSERT - SQLite.

This example demonstrates:
1. INSERT single row
2. INSERT with auto-increment
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect


create_table = CreateTableStatement(
    dialect=dialect,
    table=Table(dialect, 'users'),
    columns=[
        ColumnDefinition(dialect, 
            "id",
            IntegerType(),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect, is_auto_increment=True)),
                ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
            ],
        ),
        ColumnDefinition(dialect, "name", TextType()),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
print(f"Create table SQL: {sql}")
backend.execute(sql, params)

# ============================================================
# SECTION: Single INSERT (using InsertStatement)
# ============================================================

insert_expr = InsertStatement(
    dialect=dialect,
    into=Table(dialect, 'users'),
    columns=["name"],
    source=ValuesSource(
        [
            [Literal(dialect, "Alice")],
        ],
    ),
)
sql, params = insert_expr.to_sql()
print(f"Insert SQL: {sql}")
print(f"Params: {params}")
backend.execute(sql, params)

verify_query = QueryStatement(
    dialect=dialect,
    select=[Wildcard(dialect)],
    from_=NamedRelationRef(dialect, Table(dialect, "users")),
)
sql, params = verify_query.to_sql()
result = backend.execute(sql, params)
print(f"Result: {result.data}")

# ============================================================
# SECTION: Teardown
# ============================================================
drop_expr = DropTableStatement(dialect=dialect, table=Table(dialect, 'users'), if_exists=True)
sql, params = drop_expr.to_sql()
backend.execute(sql, params)
backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Use InsertStatement with ValuesSource for single row
# 2. Auto-increment uses PRIMARY KEY constraint
