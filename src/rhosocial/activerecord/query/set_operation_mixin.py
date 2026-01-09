# src/rhosocial/activerecord/query/set_operation_mixin.py
"""Set operation mixin for implementing ISetOperationQuery interface."""

from typing import Union, TYPE_CHECKING
from ..interface import IQuery, ISetOperationQuery

if TYPE_CHECKING:  # pragma: no cover
    from .set_operation import SetOperationQuery


class SetOperationMixin(ISetOperationQuery):
    """Mixin class that provides set operation functionality.

    This mixin implements the ISetOperationQuery interface by creating
    SetOperationQuery instances for each operation.
    """

    def union(self, other: Union[ISetOperationQuery, IQuery]) -> 'SetOperationQuery':
        """Perform a UNION operation with another query."""
        from .set_operation import SetOperationQuery
        return SetOperationQuery(self, other, "UNION")

    def intersect(self, other: Union[ISetOperationQuery, IQuery]) -> 'SetOperationQuery':
        """Perform an INTERSECT operation with another query."""
        from .set_operation import SetOperationQuery
        return SetOperationQuery(self, other, "INTERSECT")

    def except_(self, other: Union[ISetOperationQuery, IQuery]) -> 'SetOperationQuery':
        """Perform an EXCEPT operation with another query."""
        from .set_operation import SetOperationQuery
        return SetOperationQuery(self, other, "EXCEPT")

    # Operator overloading for more Pythonic syntax
    def __or__(self, other: Union[ISetOperationQuery, IQuery]) -> 'SetOperationQuery':
        """Implement the | operator for UNION."""
        return self.union(other)

    def __and__(self, other: Union[ISetOperationQuery, IQuery]) -> 'SetOperationQuery':
        """Implement the & operator for INTERSECT."""
        return self.intersect(other)

    def __sub__(self, other: Union[ISetOperationQuery, IQuery]) -> 'SetOperationQuery':
        """Implement the - operator for EXCEPT."""
        return self.except_(other)