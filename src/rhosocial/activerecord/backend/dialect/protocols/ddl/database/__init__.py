"""The database DDL protocols.

One protocol per statement expression. See
:mod:`~rhosocial.activerecord.backend.dialect.protocols.ddl` for why the
split is by statement rather than by object.
"""

from .alter_database import AlterDatabaseSupport
from .create_database import CreateDatabaseSupport
from .drop_database import DropDatabaseSupport

__all__ = [
    "AlterDatabaseSupport",
    "CreateDatabaseSupport",
    "DropDatabaseSupport",
]
