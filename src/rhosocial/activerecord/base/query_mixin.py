# src/rhosocial/activerecord/base/query_mixin.py
"""QueryMixin class providing query functionality for ActiveRecord."""

from typing import TYPE_CHECKING
from ..interface import IActiveRecord, IActiveQuery
from ..query import ActiveQuery

if TYPE_CHECKING:
    from ..query import ActiveQuery


class QueryMixin(IActiveRecord):
    """Mixin class providing query functionality for ActiveRecord models.

    Provides:
    - Query builder interface
    - Custom query class support
    """

    __query_class__ = ActiveQuery

    @classmethod
    def query(cls) -> 'IActiveQuery':
        """Create a new query instance for this model.

        Returns:
            IActiveQuery: New query instance configured for this model
        """
        return cls.__query_class__(cls)
