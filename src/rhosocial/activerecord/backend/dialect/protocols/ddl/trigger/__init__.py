"""The trigger DDL protocols.

One protocol per statement expression. See
:mod:`~rhosocial.activerecord.backend.dialect.protocols.ddl` for why the
split is by statement rather than by object.
"""

from .create_trigger import CreateTriggerSupport
from .drop_trigger import DropTriggerSupport

__all__ = [
    "CreateTriggerSupport",
    "DropTriggerSupport",
]
