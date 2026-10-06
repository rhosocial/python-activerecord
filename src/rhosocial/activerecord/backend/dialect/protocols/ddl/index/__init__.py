"""The index DDL protocols.

One protocol per statement expression. See
:mod:`~rhosocial.activerecord.backend.dialect.protocols.ddl` for why the
split is by statement rather than by object.
"""

from .create_index import CreateIndexSupport
from .drop_index import DropIndexSupport
from .fulltext import FulltextIndexSupport

__all__ = [
    "CreateIndexSupport",
    "DropIndexSupport",
    "FulltextIndexSupport",
]
