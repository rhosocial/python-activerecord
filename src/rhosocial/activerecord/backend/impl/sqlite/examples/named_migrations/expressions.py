from rhosocial.activerecord.backend.expression.statements import (
    ColumnPrimaryKeyConstraint,
)
from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
    SQLiteIntegerType,
    SQLiteTextType,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    CreateTableStatement,
    ColumnDefinition,
    ColumnConstraint,
    DropTableStatement,
)
from .....expression.objects import Table
# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_migrations/expressions.py
"""
DDL named expression functions for migration examples.

Each function receives a *dialect* and returns a DDL expression object.
These are the building blocks used by NamedMigration up()/down() methods.
"""


#: The table the custom-table migration creates when the caller names none.
#:
#: ``create_custom_table`` and ``drop_custom_table`` are the two halves of one
#: migration: the second has to drop the table the first built. Writing the
#: name down twice would be two places that have to stay in step with nothing
#: keeping them in step, and a migration that created a table its ``down()``
#: could not drop is a silent failure rather than an error. Per
#: ``.claude/rules/constants.md`` a value read from more than one function,
#: where the readings must agree, takes a module-level constant and a test
#: that pins it -- see
#: ``tests/rhosocial/activerecord_test/feature/rules/test_shared_defaults.py``.
DEFAULT_CUSTOM_TABLE_NAME: str = "custom_table"




def create_users_table(dialect):
    """CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)."""
    return CreateTableStatement(
        dialect,
        table=Table(dialect, 'users'),
        columns=[
            ColumnDefinition(dialect, 
                "id",
                SQLiteIntegerType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect))],
            ),
            ColumnDefinition(dialect, "name", SQLiteTextType(dialect)),
            ColumnDefinition(dialect, "email", SQLiteTextType(dialect)),
        ],
    )


def drop_users_table(dialect):
    """DROP TABLE IF EXISTS users."""
    return DropTableStatement(dialect, table=Table(dialect, 'users'), if_exists=True)


def create_posts_table(dialect):
    """CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT, user_id INTEGER)."""
    return CreateTableStatement(
        dialect,
        table=Table(dialect, 'posts'),
        columns=[
            ColumnDefinition(dialect, 
                "id",
                SQLiteIntegerType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect))],
            ),
            ColumnDefinition(dialect, "title", SQLiteTextType(dialect)),
            ColumnDefinition(dialect, "user_id", SQLiteIntegerType(dialect)),
        ],
    )


def drop_posts_table(dialect):
    """DROP TABLE IF EXISTS posts."""
    return DropTableStatement(dialect, table=Table(dialect, 'posts'), if_exists=True)


def create_custom_table(dialect, table_name: str = DEFAULT_CUSTOM_TABLE_NAME):
    """CREATE TABLE <table_name> (id INTEGER PRIMARY KEY, value TEXT).

    This expression accepts an extra ``table_name`` parameter, allowing
    the migration to control the target table name at runtime.
    """
    return CreateTableStatement(
        dialect,
        table=Table(dialect, table_name),
        columns=[
            ColumnDefinition(dialect, 
                "id",
                SQLiteIntegerType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect))],
            ),
            ColumnDefinition(dialect, "value", SQLiteTextType(dialect)),
        ],
    )


def drop_custom_table(dialect, table_name: str = DEFAULT_CUSTOM_TABLE_NAME):
    """DROP TABLE IF EXISTS <table_name>."""
    return DropTableStatement(dialect, table=Table(dialect, table_name), if_exists=True)
