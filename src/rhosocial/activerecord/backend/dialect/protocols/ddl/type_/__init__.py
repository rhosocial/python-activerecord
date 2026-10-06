"""The type  DDL protocols.

One protocol per statement expression. See
:mod:`~rhosocial.activerecord.backend.dialect.protocols.ddl` for why the
split is by statement rather than by object.
"""

from .alter_type import AlterTypeSupport
from .create_type import CreateTypeSupport
from .drop_type import DropTypeSupport

__all__ = [
    "AlterTypeSupport",
    "CreateTypeSupport",
    "DropTypeSupport",
]
