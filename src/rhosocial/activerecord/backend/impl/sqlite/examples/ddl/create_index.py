"""
Create an index on an existing table.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect

from rhosocial.activerecord.backend.expression import CreateTableStatement  # noqa: E402
from rhosocial.activerecord.backend.expression.statements import (  # noqa: E402
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

create_table = CreateTableStatement(
    dialect=dialect,
    table_name="users",
    columns=[
        ColumnDefinition(dialect, 
            "id",
            IntegerType(),
            constraints=[
                ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True),
                ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
            ],
        ),
        ColumnDefinition(dialect, 
            "email",
            TextType(),
            constraints=[
                ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL),
            ],
        ),
        ColumnDefinition(dialect, "name", TextType()),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import CreateIndexStatement  # noqa: E402

create_idx = CreateIndexStatement(
    dialect=dialect,
    index_name="idx_users_email",
    table_name="users",
    columns=["email"],
    unique=True,
    if_not_exists=True,
)

sql, params = create_idx.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
result = backend.execute(sql, params)
print("Index created: idx_users_email")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
