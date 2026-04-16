"""
CREATE UNIQUE INDEX - SQLite.

This example demonstrates:
1. CREATE UNIQUE INDEX on a single column
2. CREATE UNIQUE INDEX on multiple columns (composite unique)
3. Verify uniqueness constraint by attempting duplicate insert
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
dialect = backend.dialect

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    QueryExpression,
    TableExpression,
    InsertExpression,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.core import Literal, WildcardExpression
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
        ColumnDefinition('email', 'TEXT', constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ]),
        ColumnDefinition('username', 'TEXT', constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ]),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import CreateIndexExpression

# 1. CREATE UNIQUE INDEX on a single column
create_email_idx = CreateIndexExpression(
    dialect=dialect,
    index_name='idx_users_email',
    table_name='users',
    columns=['email'],
    unique=True,
    if_not_exists=True,
)
sql, params = create_email_idx.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# 2. CREATE UNIQUE INDEX on multiple columns (composite unique)
create_composite_idx = CreateIndexExpression(
    dialect=dialect,
    index_name='idx_users_username_email',
    table_name='users',
    columns=['username', 'email'],
    unique=True,
    if_not_exists=True,
)
sql, params = create_composite_idx.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================

# Create the unique indexes
sql, params = create_email_idx.to_sql()
backend.execute(sql, params)
print("Index created: idx_users_email (UNIQUE on email)")

sql, params = create_composite_idx.to_sql()
backend.execute(sql, params)
print("Index created: idx_users_username_email (UNIQUE on username, email)")

# Insert initial row
insert_expr = InsertExpression(
    dialect=dialect,
    into='users',
    columns=['email', 'username'],
    source=ValuesSource(dialect, [
        [Literal(dialect, 'alice@example.com'), Literal(dialect, 'alice')],
    ]),
)
sql, params = insert_expr.to_sql()
backend.execute(sql, params)
print("Inserted: alice@example.com / alice")

# 3. Verify uniqueness: attempt duplicate email (should fail)
try:
    duplicate_insert = InsertExpression(
        dialect=dialect,
        into='users',
        columns=['email', 'username'],
        source=ValuesSource(dialect, [
            [Literal(dialect, 'alice@example.com'), Literal(dialect, 'alice2')],
        ]),
    )
    sql, params = duplicate_insert.to_sql()
    backend.execute(sql, params)
    print("ERROR: Duplicate email was accepted (should have been rejected)")
except Exception as e:
    print(f"Uniqueness constraint enforced: {e}")

# Verify data after failed insert
verify_query = QueryExpression(
    dialect=dialect,
    select=[WildcardExpression(dialect)],
    from_=TableExpression(dialect, 'users'),
)
sql, params = verify_query.to_sql()
result = backend.execute(sql, params)
print(f"Rows in users table: {result.data}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
