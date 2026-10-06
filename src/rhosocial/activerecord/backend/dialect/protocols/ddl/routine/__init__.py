"""The routine DDL protocols.

One protocol per statement expression. See
:mod:`~rhosocial.activerecord.backend.dialect.protocols.ddl` for why the
split is by statement rather than by object.
"""

from .create_function import CreateRoutineSupport
from .drop_function import DropRoutineSupport

__all__ = [
    "CreateRoutineSupport",
    "DropRoutineSupport",
]
