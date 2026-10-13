from rhosocial.activerecord.backend.expression.statements import (
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
    ColumnUniqueConstraint,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (  # noqa: E402
    IndexDefinition,
)
from rhosocial.activerecord.backend.expression import CreateTableStatement, ColumnDefinition, ColumnConstraint
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType, TimestampType
"""
Create a table with primary key, auto-increment, and index.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================

columns = [
    ColumnDefinition(dialect, 
        name="id",
        data_type=IntegerType(),
        constraints=[
            ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect, is_auto_increment=True)),
        ],
    ),
    ColumnDefinition(dialect, 
        name="name",
        data_type=TextType(),
        constraints=[
            ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
        ],
    ),
    ColumnDefinition(dialect, 
        name="email",
        data_type=TextType(),
        constraints=[
            ColumnConstraint(dialect, branch=ColumnUniqueConstraint(dialect)),
        ],
    ),
    ColumnDefinition(dialect, 
        name="created_at",
        data_type=TimestampType(),
    ),
]

indexes = [
    IndexDefinition(dialect, 
        name="idx_users_email",
        columns=["email"],
    ),
]

create_expr = CreateTableStatement(
    dialect=dialect,
    table_name="users",
    columns=columns,
    indexes=indexes,
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
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
