"""
Query building interfaces for ActiveRecord implementation.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Generic, TypeVar, Type

ModelT = TypeVar('ModelT', bound='IActiveRecord')

class IQuery(Generic[ModelT], ABC):
    """Interface for building and executing database queries.

    Provides a fluent interface for constructing SQL queries with:
    - Conditions (WHERE clauses)
    - Sorting (ORDER BY)
    - Grouping (GROUP BY)
    - Joins
    - Pagination (LIMIT/OFFSET)
    """
    def __init__(self, model_class: Type[ModelT]):
        self.model_class = model_class
        self.conditions: List[Tuple[str, tuple]] = []
        self.order_clauses: List[str] = []
        self.group_clauses: List[str] = []
        self.having_conditions: List[Tuple[str, tuple]] = []
        self.limit_count: Optional[int] = None
        self.offset_count: Optional[int] = None
        self.join_clauses: List[str] = []
        self.select_columns: List[str] = ["*"]
        self._params: List[Any] = []  # Query parameters
        self._eager_loads: Dict[str, List[str]] = {}  # Relations to be eager loaded
        self._loaded_relations: Dict[str, Dict[int, Any]] = {}  # Cache of loaded relation data
        # Extended condition storage for OR logic support
        self.condition_groups: List[List[Tuple[str, tuple, str]]] = [[]]  # [[(condition, params, operator), ...], ...]
        self.current_group = 0

    def _log(self, level: int, msg: str, *args, **kwargs) -> None:
        """Internal logging helper"""
        pass

    @abstractmethod
    def query(self, conditions: Optional[Dict[str, Any]] = None) -> 'IQuery[ModelT]':
        """Configure query with given conditions.

        Args:
            conditions: Optional dictionary of conditions to apply

        Returns:
            Configured query instance

        Examples:
            query.query({'status': 'active', 'type': 'user'})
            # Results in: WHERE status = ? AND type = ?
        """
        pass

    @abstractmethod
    def where(self, condition: str, params: Optional[Union[tuple, List[Any]]] = None) -> 'IQuery[ModelT]':
        """Add WHERE condition to the query.

        Args:
            condition: SQL condition string with placeholders
            params: Parameter values for the condition placeholders

        Returns:
            Query instance with WHERE condition added

        Examples:
            query.where('status = ?', (1,))
            query.where('created_at > ? AND updated_at < ?', (start_date, end_date))
        """
        pass

    @abstractmethod
    def order_by(self, *clauses: str) -> 'IQuery[ModelT]':
        """Add ORDER BY clauses to the query.

        Args:
            *clauses: Order expressions (e.g., 'id DESC', 'name ASC')

        Returns:
            Query instance with ORDER BY clauses added

        Examples:
            query.order_by('created_at DESC')
            query.order_by('status ASC', 'priority DESC')
        """
        pass

    @abstractmethod
    def limit(self, count: int) -> 'IQuery[ModelT]':
        """Set result limit (LIMIT clause).

        Args:
            count: Maximum number of records to return

        Returns:
            Query instance with LIMIT clause added

        Raises:
            QueryError: If count is negative

        Examples:
            query.limit(10) # Return at most 10 records
        """
        pass

    @abstractmethod
    def offset(self, count: int) -> 'IQuery[ModelT]':
        """Set result offset (OFFSET clause).

        Args:
            count: Number of records to skip

        Returns:
            Query instance with OFFSET clause added

        Raises:
            QueryError: If count is negative

        Examples:
            query.offset(10) # Skip first 10 records
            query.limit(10).offset(20) # Records 21-30
        """
        pass

    @abstractmethod
    def one(self) -> Optional[ModelT]:
        """Execute query and return first matching record.

        Returns:
            Single model instance or None if no matches

        Raises:
            DatabaseError: If query execution fails
        """
        pass

    @abstractmethod
    def all(self) -> List[ModelT]:
        """Execute query and return all matching records.

        Returns:
            List of model instances for matching records

        Raises:
            DatabaseError: If query execution fails
        """
        pass

    @abstractmethod
    def to_dict(self, include: Optional[Set[str]] = None, exclude: Optional[Set[str]] = None) -> 'IDictQuery[ModelT]':
        """Convert query results to dictionary format.

        Args:
            include: Optional set of fields to include
            exclude: Optional set of fields to exclude

        Returns:
            DictQuery instance for dictionary results
        """
        pass

    @abstractmethod
    def one_or_fail(self) -> Optional[ModelT]:
        """Execute query and return first match, raising error if none found.

        Returns:
            Single model instance

        Raises:
            RecordNotFound: If no matching record exists
            DatabaseError: If query execution fails
        """
        pass

    @abstractmethod
    def in_list(self, column: str, values: Union[List[Any], Tuple[Any, ...]],
                empty_result: bool = True) -> 'IQuery[ModelT]':
        """Add IN condition to the query.

        Args:
            column: Column name to check
            values: List or tuple of values to match against
            empty_result: Behavior when values list is empty:
                         True - Return empty result set
                         False - Ignore this condition

        Returns:
            Query instance with IN condition added

        Examples:
            query.in_list('status', [1, 2, 3])
            query.in_list('type', ('admin', 'staff'))
        """
        pass

    @abstractmethod
    def not_in(self, column: str, values: Union[List[Any], Tuple[Any, ...]],
               empty_result: bool = False) -> 'IQuery[ModelT]':
        """Add NOT IN condition to the query.

        Args:
            column: Column name to check
            values: List or tuple of values to exclude
            empty_result: Behavior when values list is empty:
                         True - Return empty result
                         False - Ignore this condition (default)

        Returns:
            Query instance with NOT IN condition added

        Examples:
            query.not_in('status', [3, 4]) # Exclude status 3 and 4
            query.not_in('type', ['deleted', 'banned'])
        """
        pass

    @abstractmethod
    def or_where(self, condition: str, params: Optional[Union[tuple, List[Any]]] = None) -> 'IQuery[ModelT]':
        """Add OR condition to the query.

        Args:
            condition: SQL condition string with placeholders
            params: Parameter values for condition placeholders

        Returns:
            Query instance with OR condition added

        Examples:
            query.where('status = ?', [1]).or_where('status = ?', [2])
            # Results in: WHERE status = 1 OR status = 2
        """
        pass

    @abstractmethod
    def start_or_group(self) -> 'IQuery[ModelT]':
        """Start new OR condition group (with parentheses).

        Used for complex OR logic combinations with AND conditions.

        Returns:
            Query instance with new OR group started

        Examples:
            query.where('status = ?', [1])\\
                 .start_or_group()\\
                 .where('type = ?', ['admin'])\\
                 .or_where('type = ?', ['staff'])\\
                 .end_or_group()
            # Results in: WHERE status = 1 AND (type = 'admin' OR type = 'staff')
        """
        pass

    @abstractmethod
    def end_or_group(self) -> 'IQuery[ModelT]':
        """End current OR condition group.

        Must be called after start_or_group() to close the parentheses.

        Returns:
            Query instance with current OR group ended
        """
        pass

    @abstractmethod
    def between(self, column: str, start: Any, end: Any) -> 'IQuery[ModelT]':
        """Add a BETWEEN condition to the query.

        Args:
            column: Column name
            start: Start value
            end: End value

        Returns:
            Query instance with BETWEEN condition added

        Examples:
            query.between('age', 18, 30)
            # Results in: WHERE age BETWEEN ? AND ?
        """
        pass

    @abstractmethod
    def not_between(self, column: str, start: Any, end: Any) -> 'IQuery[ModelT]':
        """Add a NOT BETWEEN condition to the query.

        Args:
            column: Column name
            start: Start value
            end: End value

        Returns:
            Query instance with NOT BETWEEN condition added

        Examples:
            query.not_between('price', 100, 200)
            # Results in: WHERE price NOT BETWEEN ? AND ?
        """
        pass

    @abstractmethod
    def like(self, column: str, pattern: str) -> 'IQuery[ModelT]':
        """Add a LIKE condition to the query.

        Args:
            column: Column name
            pattern: LIKE pattern (can include % and _ wildcards)

        Returns:
            Query instance with LIKE condition added

        Examples:
            query.like('name', 'John%')
            # Results in: WHERE name LIKE ?
        """
        pass

    @abstractmethod
    def not_like(self, column: str, pattern: str) -> 'IQuery[ModelT]':
        """Add a NOT LIKE condition to the query.

        Args:
            column: Column name  
            pattern: LIKE pattern (can include % and _ wildcards)

        Returns:
            Query instance with NOT LIKE condition added

        Examples:
            query.not_like('email', '%@spam.com')
            # Results in: WHERE email NOT LIKE ?
        """
        pass

    @abstractmethod
    def is_null(self, column: str) -> 'IQuery[ModelT]':
        """Add an IS NULL condition to the query.

        Args:
            column: Column name

        Returns:
            Query instance with IS NULL condition added

        Examples:
            query.is_null('deleted_at')
            # Results in: WHERE deleted_at IS NULL
        """
        pass

    @abstractmethod 
    def is_not_null(self, column: str) -> 'IQuery[ModelT]':
        """Add an IS NOT NULL condition to the query.

        Args:
            column: Column name

        Returns:
            Query instance with IS NOT NULL condition added

        Examples:
            query.is_not_null('email')
            # Results in: WHERE email IS NOT NULL
        """
        pass


class IDictQuery(Generic[ModelT], ABC):
    """Interface for queries that return dictionary results instead of model instances.

    Useful for operations that don't require full model instantiation.
    """
    @abstractmethod
    def all(self) -> List[Dict[str, Any]]:
        """Execute query and return all results as dictionaries.

        Returns:
            List of dictionaries containing record data
        """
        pass

    @abstractmethod
    def one(self) -> Optional[Dict[str, Any]]:
        """Execute query and return first result as dictionary.

        Returns:
            Dictionary containing record data or None if no match
        """
        pass