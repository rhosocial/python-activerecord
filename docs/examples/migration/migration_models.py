# docs/examples/migration/migration_models.py
"""Importable model + migration functions used by 03_cli_migrate.py.

Kept in a separate module because the CLI resolves migration functions and the
model by fully qualified name (module:Class / module:function), which requires
an importable module rather than __main__.
"""
import os
from typing import Annotated, Optional

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType
from rhosocial.activerecord.backend.migration import migration, MigrationDirection


# The model's configured backend supplies the connection to the CLI via --model.
class CliUser(ActiveRecord):
    @classmethod
    def table_name(cls) -> str:
        return "cli_users"

    id: Annotated[Optional[int], UseSqlType(IntegerType())] = None
    name: Annotated[str, UseSqlType(VarCharType(length=64))]


@migration("v001_create_cli_users")
def create_cli_users(ctx):
    if ctx.direction == MigrationDirection.UP:
        ctx.apply(CliUser.create_table_statement(backend=ctx.backend))
    else:
        ctx.apply(CliUser.drop_table_statement(if_exists=True, backend=ctx.backend))
