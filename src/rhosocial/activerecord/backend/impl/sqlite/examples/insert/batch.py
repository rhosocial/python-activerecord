"""
Batch insert with multiple rows.
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

from rhosocial.activerecord.backend.expression import CreateTableExpression
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

create_table = CreateTableExpression(
    dialect=dialect,
    table_name='users',
    columns=[
        ColumnDefinition('id', 'INTEGER', constraints=[
            ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
            ColumnConstraint(ColumnConstraintType.NOT_NULL, is_auto_increment=True),
        ]),
        ColumnDefinition('name', 'TEXT', constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ]),
        ColumnDefinition('email', 'TEXT'),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
print(f"Create table SQL: {sql}")
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (
    InsertExpression,
    ValuesSource,
    TableExpression,
    QueryExpression,
)
from rhosocial.activerecord.backend.expression.core import Literal, WildcardExpression

insert_expr = InsertExpression(
    dialect=dialect,
    into=TableExpression(dialect, 'users'),
    source=ValuesSource(
        dialect,
        [
            [Literal(dialect, 'Alice'), Literal(dialect, 'alice@example.com')],
            [Literal(dialect, 'Bob'), Literal(dialect, 'bob@example.com')],
            [Literal(dialect, 'Charlie'), Literal(dialect, 'charlie@example.com')],
        ],
    ),
    columns=['name', 'email'],
)

sql, params = insert_expr.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
result = backend.execute(sql, params)
print(f"Affected rows: {result.affected_rows}")

# Verify
verify_query = QueryExpression(
    dialect=dialect,
    select=[WildcardExpression(dialect)],
    from_=TableExpression(dialect, 'users'),
)
options = ExecutionOptions(stmt_type=StatementType.DQL)
sql, params = verify_query.to_sql()
result = backend.execute(sql, params, options=options)
print(f"Total rows in table: {len(result.data) if result.data else 0}")
for row in result.data or []:
    print(f"  {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
