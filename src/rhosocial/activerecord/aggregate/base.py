"""Base class for aggregate operations."""
from typing import Any, Dict, List, Optional, Type, Union, Generic, TypeVar

ModelT = TypeVar('ModelT')

class AggregateBase(Generic[ModelT]):
    """Base class for aggregate operations.

    Separates aggregate logic from model to follow composition over inheritance.

    Args:
        model_class: The ActiveRecord model class to perform aggregations on
    """

    def __init__(self, model_class: Type[ModelT]):
        self.model_class = model_class

    def _build_query(self, func: str, column: str,
                    group_columns: Optional[Union[str, List[str]]] = None,
                    condition: Optional[str] = None,
                    params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Build and execute aggregate query.

        Args:
            func: Aggregate function name (SUM, AVG, etc.)
            column: Column to aggregate
            group_columns: Optional grouping columns
            condition: Optional WHERE clause
            params: WHERE clause parameters

        Returns:
            Query results as list of dictionaries
        """
        select_parts = []
        if group_columns:
            columns = [group_columns] if isinstance(group_columns, str) else group_columns
            select_parts.extend(columns)

        select_parts.append(f"{func}({column}) as result")
        query = self.model_class.query().select(", ".join(select_parts))

        if condition:
            query = query.where(condition, params)

        if group_columns:
            query = query.group_by(*([group_columns] if isinstance(group_columns, str) else group_columns))

        return query.to_dict().all()

    def sum(self, column: str, condition: Optional[str] = None,
            params: Optional[tuple] = None) -> Optional[Union[int, float]]:
        """Calculate sum of column values.

        Args:
            column: Column to sum
            condition: Optional WHERE clause
            params: WHERE clause parameters

        Returns:
            Sum value or None if no records

        Example:
            total = User.aggregate().sum('balance', 'status = ?', ('active',))
        """
        result = self._build_query("SUM", column, None, condition, params)
        return result[0]["result"] if result else None

    def avg(self, column: str, condition: Optional[str] = None,
            params: Optional[tuple] = None) -> Optional[float]:
        """Calculate average of column values.

        Args:
            column: Column to average
            condition: Optional WHERE clause
            params: WHERE clause parameters

        Returns:
            Average value or None if no records

        Example:
            avg_age = User.aggregate().avg('age', 'status = ?', ('active',))
        """
        result = self._build_query("AVG", column, None, condition, params)
        return result[0]["result"] if result else None

    def max(self, column: str, condition: Optional[str] = None,
            params: Optional[tuple] = None) -> Optional[Any]:
        """Get maximum value in column.

        Args:
            column: Column to get maximum from
            condition: Optional WHERE clause
            params: WHERE clause parameters

        Returns:
            Maximum value or None if no records

        Example:
            highest = Order.aggregate().max('amount')
        """
        result = self._build_query("MAX", column, None, condition, params)
        return result[0]["result"] if result else None

    def min(self, column: str, condition: Optional[str] = None,
            params: Optional[tuple] = None) -> Optional[Any]:
        """Get minimum value in column.

        Args:
            column: Column to get minimum from
            condition: Optional WHERE clause
            params: WHERE clause parameters

        Returns:
            Minimum value or None if no records

        Example:
            lowest = Product.aggregate().min('price')
        """
        result = self._build_query("MIN", column, None, condition, params)
        return result[0]["result"] if result else None

    def count_by(self, group_columns: Union[str, List[str]],
                condition: Optional[str] = None,
                params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Group and count records.

        Args:
            group_columns: Column(s) to group by
            condition: Optional WHERE clause
            params: WHERE clause parameters

        Returns:
            List of dictionaries with group values and counts

        Example:
            stats = Order.aggregate().count_by(['status', 'type'])
        """
        return self._build_query("COUNT", "*", group_columns, condition, params)

    def sum_by(self, column: str, group_columns: Union[str, List[str]],
              condition: Optional[str] = None,
              params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Group and sum column values.

        Args:
            column: Column to sum
            group_columns: Column(s) to group by
            condition: Optional WHERE clause
            params: WHERE clause parameters

        Returns:
            List of dictionaries with group values and sums

        Example:
            totals = Order.aggregate().sum_by('amount', 'customer_id')
        """
        return self._build_query("SUM", column, group_columns, condition, params)

    def avg_by(self, column: str, group_columns: Union[str, List[str]],
              condition: Optional[str] = None,
              params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Group and average column values.

        Args:
            column: Column to average
            group_columns: Column(s) to group by
            condition: Optional WHERE clause
            params: WHERE clause parameters

        Returns:
            List of dictionaries with group values and averages

        Example:
            averages = Product.aggregate().avg_by('price', 'category')
        """
        return self._build_query("AVG", column, group_columns, condition, params)