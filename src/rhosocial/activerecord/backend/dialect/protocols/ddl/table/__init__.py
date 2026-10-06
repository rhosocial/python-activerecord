"""The table DDL protocols.

One protocol per statement expression. See
:mod:`~rhosocial.activerecord.backend.dialect.protocols.ddl` for why the
split is by statement rather than by object.
"""

from .alter_table import AlterTableSupport
from .create_table import CreateTableSupport
from .create_table_as import CreateTableAsSupport
from .create_table_clone import CreateTableCloneSupport
from .create_table_like import CreateTableLikeSupport
from .create_table_using_template import CreateTableUsingTemplateSupport
from .drop_table import DropTableSupport

__all__ = [
    "AlterTableSupport",
    "CreateTableSupport",
    "CreateTableAsSupport",
    "CreateTableCloneSupport",
    "CreateTableLikeSupport",
    "CreateTableUsingTemplateSupport",
    "DropTableSupport",
]
