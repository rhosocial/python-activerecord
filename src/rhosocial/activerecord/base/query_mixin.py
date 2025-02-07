"""QueryMixin class providing query functionality for ActiveRecord."""

from ..interface import IActiveRecord
from ..query import ActiveQuery


class QueryMixin(IActiveRecord):
    """Mixin class providing query functionality for ActiveRecord models.

    Provides:
    - Query builder interface
    - Custom query class support
    """

    __query_class__ = ActiveQuery

    @classmethod
    def query(cls) -> 'ActiveQuery':
        """Create a new query instance for this model.

        Returns:
            ActiveQuery: New query instance configured for this model
        """
        return cls.__query_class__(cls)