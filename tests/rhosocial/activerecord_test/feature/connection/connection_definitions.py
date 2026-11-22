# tests/rhosocial/activerecord_test/feature/connection/fixtures/definitions.py
"""L1 fixture definitions for the connection and pool tests.

The definitions receive only a ``dialect``: they build the tables the
connection fixtures need and know nothing about pools, backends or execution.
"""
from rhosocial.activerecord.base.derivation import integer_auto_increment_parts  # noqa: E402

from rhosocial.activerecord.backend.expression import (
    ColumnConstraint as Constraint,
    ColumnDefinition as Column,
    CreateTableStatement as CreateTable,
    DropTableStatement as DropTable,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    ColumnNotNullConstraint as NotNull,
    ColumnPrimaryKeyConstraint as PrimaryKey,
)
from rhosocial.activerecord.backend.expression.types import (
    IntegerType as Int,
    TextType as Text,
)


class Definition:
    """Base class for this directory's table definitions."""

    table_name = ""
    if_not_exists = False

    def __init__(self, dialect):
        self.dialect = dialect
        self.create_table = CreateTable(
            dialect,
            table=Table(dialect, self.table_name),
            columns=self.columns(),
            if_not_exists=self.if_not_exists,
        )
        self.drop_table = DropTable(dialect, table=Table(dialect, self.table_name), if_exists=True)

    def columns(self):
        raise NotImplementedError

    def auto_pk(self, name="id"):
        data_type, attributes = integer_auto_increment_parts(self.dialect, Int(self.dialect))
        return Column(
            self.dialect, name, data_type,
            constraints=[Constraint(self.dialect, branch=PrimaryKey(self.dialect))],
            attributes=attributes,
        )


    def not_null(self, name, sql_type):
        return Column(
            self.dialect,
            name,
            sql_type,
            constraints=[Constraint(self.dialect, branch=NotNull(self.dialect))],
        )


class UsersDefinition(Definition):
    table_name = "users"

    def columns(self):
        return [
            self.auto_pk(),
            self.not_null("name", Text(self.dialect)),
            self.not_null("email", Text(self.dialect)),
        ]


class PostsDefinition(Definition):
    table_name = "posts"

    def columns(self):
        return [
            self.auto_pk(),
            self.not_null("title", Text(self.dialect)),
            self.not_null("user_id", Int(self.dialect)),
        ]


class CommentsDefinition(Definition):
    table_name = "comments"

    def columns(self):
        return [
            self.auto_pk(),
            self.not_null("content", Text(self.dialect)),
            self.not_null("post_id", Int(self.dialect)),
        ]


class PoolUsersDefinition(Definition):
    table_name = "pool_users"
    if_not_exists = True

    def columns(self):
        return [
            self.auto_pk(),
            self.not_null("name", Text(self.dialect)),
            self.not_null("email", Text(self.dialect)),
        ]


class PoolPostsDefinition(Definition):
    table_name = "pool_posts"
    if_not_exists = True

    def columns(self):
        return [
            self.auto_pk(),
            self.not_null("title", Text(self.dialect)),
            self.not_null("user_id", Int(self.dialect)),
        ]


#: The tables ``configured_backend`` creates.
CONNECTION_DEFINITIONS = (UsersDefinition, PostsDefinition, CommentsDefinition)

#: The tables the pool fixtures create.
POOL_DEFINITIONS = (PoolUsersDefinition, PoolPostsDefinition)
