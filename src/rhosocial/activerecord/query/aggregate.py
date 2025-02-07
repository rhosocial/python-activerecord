"""Aggregate query methods implementation."""
from typing import Optional, Union, Any
from ..interface import ModelT, IQuery


class AggregateQueryMixin(IQuery[ModelT]):
    """Query methods for aggregate operations."""

    def sum(self, column: str) -> Optional[Union[int, float]]:
        """Execute SUM query."""
        original_select = self.select_columns
        self.select_columns = [f"SUM({column}) as sum_result"]
        sql, params = self.build()
        self.select_columns = original_select

        result = self.model_class.backend().fetch_one(sql, params)
        return result["sum_result"] if result else None

    def avg(self, column: str) -> Optional[float]:
        """Execute AVG query."""
        original_select = self.select_columns
        self.select_columns = [f"AVG({column}) as avg_result"]
        sql, params = self.build()
        self.select_columns = original_select

        result = self.model_class.backend().fetch_one(sql, params)
        return result["avg_result"] if result else None

    def max(self, column: str) -> Optional[Any]:
        """Execute MAX query."""
        original_select = self.select_columns
        self.select_columns = [f"MAX({column}) as max_result"]
        sql, params = self.build()
        self.select_columns = original_select

        result = self.model_class.backend().fetch_one(sql, params)
        return result["max_result"] if result else None

    def min(self, column: str) -> Optional[Any]:
        """Execute MIN query."""
        original_select = self.select_columns
        self.select_columns = [f"MIN({column}) as min_result"]
        sql, params = self.build()
        self.select_columns = original_select

        result = self.model_class.backend().fetch_one(sql, params)
        return result["min_result"] if result else None