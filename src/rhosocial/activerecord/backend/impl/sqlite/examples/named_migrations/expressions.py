from rhosocial.activerecord.backend.expression.statements import (
    ColumnPrimaryKeyConstraint,
)
from .....expression.objects import Table
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
# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_migrations/expressions.py
"""
DDL named expression functions for migration examples.

Each function receives a *dialect* and returns a DDL expression object.
These are the building blocks used by NamedMigration up()/down() methods.
"""




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


def create_custom_table(dialect, table_name: str = "custom_table"):
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


def drop_custom_table(dialect, table_name: str = "custom_table"):
    """DROP TABLE IF EXISTS <table_name>."""
    return DropTableStatement(dialect, table=Table(dialect, table_name), if_exists=True)
