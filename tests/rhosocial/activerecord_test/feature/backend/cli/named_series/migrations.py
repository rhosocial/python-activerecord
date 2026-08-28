# tests/rhosocial/activerecord_test/feature/backend/cli/named_series/migrations.py
"""Named migration fixtures (named-migration layer).

Contains DDL named expressions (used by up()/down()) and NamedMigration
subclasses.  Running these via the CLI creates the ``users``/``posts``
tables that the queries/procedures/graphs depend on.
"""

from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    CreateTableExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
    DropTableExpression,
)
from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
    SQLiteIntegerType,
    SQLiteTextType,
)
from rhosocial.activerecord.backend.migration import (
    NamedMigration,
    MigrationContext,
    AsyncNamedMigration,
    AsyncMigrationContext,
)


# --- DDL named expressions ------------------------------------------------


def create_users_table(dialect):
    """CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)."""
    return CreateTableExpression(
        dialect,
        table="users",
        columns=[
            ColumnDefinition(
                "id", SQLiteIntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)],
            ),
            ColumnDefinition("name", SQLiteTextType()),
            ColumnDefinition("email", SQLiteTextType()),
        ],
    )


def drop_users_table(dialect):
    """DROP TABLE IF EXISTS users."""
    return DropTableExpression(dialect, table="users", if_exists=True)


def create_posts_table(dialect):
    """CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT, user_id INTEGER)."""
    return CreateTableExpression(
        dialect,
        table="posts",
        columns=[
            ColumnDefinition(
                "id", SQLiteIntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)],
            ),
            ColumnDefinition("title", SQLiteTextType()),
            ColumnDefinition("user_id", SQLiteIntegerType()),
        ],
    )


def drop_posts_table(dialect):
    """DROP TABLE IF EXISTS posts."""
    return DropTableExpression(dialect, table="posts", if_exists=True)


# --- NamedMigration classes -------------------------------------------------


class V001CreateUsers(NamedMigration):
    """Create the ``users`` table."""

    version = "v001_create_users"

    def up(self, ctx: MigrationContext) -> None:
        ctx.execute(
            "rhosocial.activerecord_test.feature.backend.cli.named_series"
            ".migrations.create_users_table"
        )

    def down(self, ctx: MigrationContext) -> None:
        ctx.execute(
            "rhosocial.activerecord_test.feature.backend.cli.named_series"
            ".migrations.drop_users_table"
        )


class V002CreatePosts(NamedMigration):
    """Create the ``posts`` table (depends on users)."""

    version = "v002_create_posts"
    dependencies = ["v001_create_users"]

    def up(self, ctx: MigrationContext) -> None:
        ctx.execute(
            "rhosocial.activerecord_test.feature.backend.cli.named_series"
            ".migrations.create_posts_table"
        )

    def down(self, ctx: MigrationContext) -> None:
        ctx.execute(
            "rhosocial.activerecord_test.feature.backend.cli.named_series"
            ".migrations.drop_posts_table"
        )


class AsyncV001CreateUsers(AsyncNamedMigration):
    """Async variant that creates the ``users`` table."""

    version = "av001_create_users"

    async def up(self, ctx: AsyncMigrationContext) -> None:
        await ctx.execute(
            "rhosocial.activerecord_test.feature.backend.cli.named_series"
            ".migrations.create_users_table"
        )

    async def down(self, ctx: AsyncMigrationContext) -> None:
        await ctx.execute(
            "rhosocial.activerecord_test.feature.backend.cli.named_series"
            ".migrations.drop_users_table"
        )
