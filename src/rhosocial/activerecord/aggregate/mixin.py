"""Mixin class for providing aggregate functionality."""
from ..interface import IActiveRecord
from .base import AggregateBase


class AggregateMixin(IActiveRecord):
    """Mixin providing access to aggregate operations via composition.

    Example:
        class Order(AggregateMixin, ActiveRecord):
            ...

        # Usage:
        total = Order.aggregate().sum('amount')
        stats = Order.aggregate().count_by('status')
    """

    @classmethod
    def aggregate(cls) -> AggregateBase:
        """Get aggregate operations handler.

        Returns:
            AggregateBase instance for performing aggregations
        """
        return AggregateBase(cls)