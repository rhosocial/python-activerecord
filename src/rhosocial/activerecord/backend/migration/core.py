# src/rhosocial/activerecord/backend/migration/core.py
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.named_expression.procedure import (
    AsyncProcedure,
    AsyncProcedureContext,
    Procedure,
    ProcedureContext,
)

if TYPE_CHECKING:
    from .context import AsyncMigrationContext, MigrationContext


class MigrationDirection(str, Enum):
    """Execution direction for a named migration.

    Uses str mixin for direct JSON serialization in record stores.
    """

    UP = "up"
    DOWN = "down"


class NamedMigration(Procedure):
    """Stateful migration base class.

    Users inherit this class and implement ``up()`` and ``down()`` methods.
    ``version`` uniquely identifies the migration (recommended format:
    ``v001_create_users``). ``dependencies`` lists prerequisite migration
    versions that the Runner validates before execution.

    The base ``run(ctx)`` dispatches to ``up()`` or ``down()`` based on
    ``ctx.direction``, so users never deal with direction parameters directly.
    """

    version: str = ""
    dependencies: list[str] = []

    def up(self, ctx: MigrationContext) -> None:
        raise NotImplementedError

    def down(self, ctx: MigrationContext) -> None:
        raise NotImplementedError

    def run(self, ctx: ProcedureContext) -> None:
        if ctx.direction == MigrationDirection.UP:
            self.up(ctx)
        else:
            self.down(ctx)


class AsyncNamedMigration(AsyncProcedure):
    """Asynchronous stateful migration base class.

    Async counterpart of :class:`NamedMigration`. Users inherit this class
    and implement ``async def up()`` and ``async def down()`` methods using
    ``await ctx.execute(...)`` against an :class:`AsyncMigrationContext`.

    ``AsyncNamedMigration`` is resolved by
    :class:`AsyncNamedMigrationResolver` and executed by
    :class:`AsyncMigrationRunner`. Synchronous migrations
    (:class:`NamedMigration`) must use :class:`MigrationRunner` instead —
    they cannot be run through the async runner.
    """

    version: str = ""
    dependencies: list[str] = []

    async def up(self, ctx: AsyncMigrationContext) -> None:
        raise NotImplementedError

    async def down(self, ctx: AsyncMigrationContext) -> None:
        raise NotImplementedError

    async def run(self, ctx: AsyncProcedureContext) -> None:
        if ctx.direction == MigrationDirection.UP:
            await self.up(ctx)
        else:
            await self.down(ctx)