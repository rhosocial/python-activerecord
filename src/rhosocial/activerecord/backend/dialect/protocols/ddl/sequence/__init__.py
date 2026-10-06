"""The sequence DDL protocols.

One protocol per statement expression. See
:mod:`~rhosocial.activerecord.backend.dialect.protocols.ddl` for why the
split is by statement rather than by object.
"""

from .alter_sequence import AlterSequenceSupport
from .create_sequence import CreateSequenceSupport
from .drop_sequence import DropSequenceSupport

__all__ = [
    "AlterSequenceSupport",
    "CreateSequenceSupport",
    "DropSequenceSupport",
]
