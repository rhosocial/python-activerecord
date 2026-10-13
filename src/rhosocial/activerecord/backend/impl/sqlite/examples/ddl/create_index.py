from rhosocial.activerecord.backend.expression.statements import (
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
)
from rhosocial.activerecord.backend.expression import CreateIndexStatement
from rhosocial.activerecord.backend.expression.statements import ColumnDefinition, ColumnConstraint
from rhosocial.activerecord.backend.expression import CreateTableStatement
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
"""
Create an index on an existing table.
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
        ColumnDefinition(dialect, "name", TextType()),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================

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
