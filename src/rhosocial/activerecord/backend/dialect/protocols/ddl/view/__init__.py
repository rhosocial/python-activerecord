"""The view DDL protocols.

One protocol per statement expression. See
:mod:`~rhosocial.activerecord.backend.dialect.protocols.ddl` for why the
split is by statement rather than by object.
"""

from .create_view import CreateViewSupport
from .drop_view import DropViewSupport
from .materialized_view import MaterializedViewSupport

__all__ = [
    "CreateViewSupport",
    "DropViewSupport",
    "MaterializedViewSupport",
]
