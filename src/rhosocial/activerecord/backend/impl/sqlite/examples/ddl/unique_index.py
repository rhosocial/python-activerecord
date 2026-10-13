from rhosocial.activerecord.backend.expression.statements import (
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
)
from .....expression.objects import Table
from rhosocial.activerecord.backend.expression import CreateIndexStatement
from rhosocial.activerecord.backend.expression.statements import ColumnDefinition, ColumnConstraint
from rhosocial.activerecord.backend.expression.core import Literal, Wildcard
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.expression import (
    CreateTableStatement,
    QueryStatement,
    InsertStatement,
    ValuesSource,
)
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
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

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect


create_table = CreateTableStatement(
    dialect=dialect,
    table_name="users",
    columns=[
        ColumnDefinition(dialect, 
            "id",
            IntegerType(),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect, is_auto_increment=True)),
                ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
            ],
        ),
        ColumnDefinition(dialect, 
            "email",
            TextType(),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
            ],
        ),
        ColumnDefinition(dialect, 
            "username",
            TextType(),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
            ],
        ),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================

# 1. CREATE UNIQUE INDEX on a single column
create_email_idx = CreateIndexStatement(
    dialect=dialect,
    index_name="idx_users_email",
    table_name="users",
    columns=["email"],
    unique=True,
    if_not_exists=True,
)
sql, params = create_email_idx.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# 2. CREATE UNIQUE INDEX on multiple columns (composite unique)
create_composite_idx = CreateIndexStatement(
    dialect=dialect,
    index_name="idx_users_username_email",
    table_name="users",
    columns=["username", "email"],
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
insert_expr = InsertStatement(
    dialect=dialect,
    into=Table(dialect, 'users'),
    columns=["email", "username"],
    source=ValuesSource(
        [
            [Literal(dialect, "alice@example.com"), Literal(dialect, "alice")],
        ],
    ),
)
sql, params = insert_expr.to_sql()
backend.execute(sql, params)
print("Inserted: alice@example.com / alice")

# 3. Verify uniqueness: attempt duplicate email (should fail)
try:
    duplicate_insert = InsertStatement(
        dialect=dialect,
        into=Table(dialect, 'users'),
        columns=["email", "username"],
        source=ValuesSource(
            [
                [Literal(dialect, "alice@example.com"), Literal(dialect, "alice2")],
            ],
        ),
    )
    sql, params = duplicate_insert.to_sql()
    backend.execute(sql, params)
    print("ERROR: Duplicate email was accepted (should have been rejected)")
except Exception as e:
    print(f"Uniqueness constraint enforced: {e}")

# Verify data after failed insert
verify_query = QueryStatement(
    dialect=dialect,
    select=[Wildcard(dialect)],
    from_=NamedRelationRef(dialect, Table(dialect, "users")),
)
sql, params = verify_query.to_sql()
result = backend.execute(sql, params)
print(f"Rows in users table: {result.data}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
