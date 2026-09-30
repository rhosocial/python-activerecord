"""
Create a table with primary key, auto-increment, and index.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType, TimestampType
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect


# Version-gated features (RETURNING, JSON1, math functions) read the
# dialect version, which is only known after the server is inspected.
backend.introspect_and_adapt()
# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import (  # noqa: E402
    CreateIndexExpression,
    CreateTableExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

columns = [
    ColumnDefinition(dialect, 
        name="id",
        data_type=IntegerType(dialect),
        constraints=[
            ColumnConstraint(dialect, 
                constraint_type=ColumnConstraintType.PRIMARY_KEY,
                is_auto_increment=True,
            ),
        ],
    ),
    ColumnDefinition(dialect, 
        name="name",
        data_type=TextType(dialect),
        constraints=[
            ColumnConstraint(dialect, constraint_type=ColumnConstraintType.NOT_NULL),
        ],
    ),
    ColumnDefinition(dialect, 
        name="email",
        data_type=TextType(dialect),
        constraints=[
            ColumnConstraint(dialect, constraint_type=ColumnConstraintType.UNIQUE),
        ],
    ),
    ColumnDefinition(dialect, 
        name="created_at",
        data_type=TimestampType(dialect),
    ),
]

create_expr = CreateTableExpression(
    dialect=dialect,
    table="users",
    columns=columns,
    if_not_exists=True,
)

sql, params = create_expr.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
result = backend.execute(sql, params)
print("Table created: users")

# ============================================================
# SECTION: Adding an index
# ============================================================
# SQLite does not accept index definitions inside CREATE TABLE. Other dialects
# take them via CreateTableExpression(indexes=[...]) and the
# UnsupportedFeatureError says as much; on SQLite, create the index separately.
create_index_expr = CreateIndexExpression(
    dialect=dialect,
    index_name="idx_users_email",
    table_name="users",
    columns=["email"],
    if_not_exists=True,
)
sql, params = create_index_expr.to_sql()
print(f"Index SQL: {sql}")
backend.execute(sql, params)
print("Index created: idx_users_email")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
