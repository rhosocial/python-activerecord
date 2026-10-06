"""The domain DDL protocols.

One protocol per statement expression. See
:mod:`~rhosocial.activerecord.backend.dialect.protocols.ddl` for why the
split is by statement rather than by object.
"""

from .alter_domain import AlterDomainSupport
from .create_domain import CreateDomainSupport
from .drop_domain import DropDomainSupport

__all__ = [
    "AlterDomainSupport",
    "CreateDomainSupport",
    "DropDomainSupport",
]
