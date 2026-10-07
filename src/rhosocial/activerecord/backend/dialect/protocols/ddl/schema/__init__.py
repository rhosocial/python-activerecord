"""The schema DDL protocols.

One protocol per statement expression. See
:mod:`~rhosocial.activerecord.backend.dialect.protocols.ddl` for why the
split is by statement rather than by object.
"""

from .create_schema import CreateSchemaSupport
from .drop_schema import DropSchemaSupport

__all__ = [
    "CreateSchemaSupport",
    "DropSchemaSupport",
]
