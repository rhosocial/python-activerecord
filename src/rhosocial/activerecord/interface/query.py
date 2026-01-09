# src/rhosocial/activerecord/interface/query.py
"""
Query building interfaces for ActiveRecord implementation.
"""
from abc import ABC, abstractmethod
from threading import local
from typing import Any, Dict, List, Optional, Tuple, Union, TypeVar, Type, Iterator, ItemsView, KeysView, \
    ValuesView, Mapping, overload
from typing import Protocol
from typing_extensions import runtime_checkable

from .model import IActiveRecord
from ..backend.base import StorageBackend
from ..backend.expression.bases import ToSQLProtocol, BaseExpression, SQLPredicate
from ..backend.expression.query_parts import WhereClause, GroupByHavingClause, OrderByClause, LimitOffsetClause

K = TypeVar('K')
V = TypeVar('V')


class ThreadSafeDict(Dict[K, V]):
    """A thread-safe dictionary that behaves exactly like a normal dict."""

    def __init__(self, *args, **kwargs):
        """Initialize thread-safe dictionary.

        Supports same initialization as dict:
        - Empty: ThreadSafeDict()
        - From mapping: ThreadSafeDict({'a': 1})
        - From iterable: ThreadSafeDict([('a', 1), ('b', 2)])
        - From kwargs: ThreadSafeDict(a=1, b=2)
        """
        super().__init__(*args, **kwargs)
        self._local = local()
        if not hasattr(self._local, 'data'):
            self._local.data = {}
        if args or kwargs:
            self.update(*args, **kwargs)

    def __ensure_data(self) -> dict:
        """Ensure thread-local data exists.

        Returns:
            dict: Thread-local dictionary
        """
        if not hasattr(self._local, 'data'):
            self._local.data = {}
        return self._local.data

    def __getitem__(self, key: K) -> V:
        return self.__ensure_data()[key]

    def __setitem__(self, key: K, value: V) -> None:
        self.__ensure_data()[key] = value

    def __delitem__(self, key: K) -> None:
        del self.__ensure_data()[key]

    def __iter__(self) -> Iterator[K]:
        return iter(self.__ensure_data())

    def __len__(self) -> int:
        return len(self.__ensure_data())

    def __contains__(self, key: K) -> bool:
        return key in self.__ensure_data()

    def __bool__(self) -> bool:
        return bool(self.__ensure_data())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (Dict, ThreadSafeDict)):
            return NotImplemented
        return self.__ensure_data() == other

    def __repr__(self) -> str:
        return f"ThreadSafeDict({repr(self.__ensure_data())})"

    def __str__(self) -> str:
        return str(self.__ensure_data())

    # Standard dict methods
    def clear(self) -> None:
        """Remove all items from the dictionary."""
        if hasattr(self._local, 'data'):
            self._local.data.clear()

    def copy(self) -> 'ThreadSafeDict[K, V]':
        """Return a shallow copy of the dictionary."""
        result = ThreadSafeDict()
        result.update(self.__ensure_data())
        return result

    def get(self, key: K, default: Any = None) -> Optional[V]:
        """Return value for key if it exists, else default."""
        return self.__ensure_data().get(key, default)

    def items(self) -> ItemsView[K, V]:
        """Return a view of dictionary's items (key-value pairs)."""
        return self.__ensure_data().items()

    def keys(self) -> KeysView[K]:
        """Return a view of dictionary's keys."""
        return self.__ensure_data().keys()

    def values(self) -> ValuesView[V]:
        """Return a view of dictionary's values."""
        return self.__ensure_data().values()

    def pop(self, key: K, default: Any = ...) -> V:
        """Remove specified key and return the corresponding value.

        If default is provided and key doesn't exist, return default.
        If default is not provided and key doesn't exist, raise KeyError.
        """
        if default is ...:
            return self.__ensure_data().pop(key)
        return self.__ensure_data().pop(key, default)

    def popitem(self) -> Tuple[K, V]:
        """Remove and return an arbitrary (key, value) pair.

        Raises:
            KeyError: If dictionary is empty
        """
        return self.__ensure_data().popitem()

    def setdefault(self, key: K, default: V = None) -> V:
        """Return value for key if it exists, else set and return default."""
        return self.__ensure_data().setdefault(key, default)

    def update(self, *args, **kwargs) -> None:
        """Update dictionary with elements from args and kwargs.

        Args can be:
        - another dictionary
        - an iterable of key/value pairs
        - keyword arguments
        """
        data = self.__ensure_data()
        if args:
            if len(args) > 1:
                raise TypeError('update expected at most 1 argument, got ' + str(len(args)))
            other = args[0]
            if isinstance(other, Mapping):
                for key in other:
                    data[key] = other[key]
            elif hasattr(other, 'keys'):
                for key in other.keys():
                    data[key] = other[key]
            else:
                for key, value in other:
                    data[key] = value
        for key, value in kwargs.items():
            data[key] = value

    # Additional useful methods
    def to_dict(self) -> Dict[K, V]:
        """Convert to a regular dictionary."""
        return dict(self.__ensure_data())

    def set_many(self, items: List[Tuple[K, V]]) -> None:
        """Set multiple items at once from a list of tuples."""
        data = self.__ensure_data()
        for key, value in items:
            data[key] = value

    def get_many(self, keys: List[K], default: Any = None) -> List[V]:
        """Get multiple values at once.

        Args:
            keys: List of keys to retrieve
            default: Default value for missing keys

        Returns:
            List of values corresponding to the keys
        """
        data = self.__ensure_data()
        return [data.get(key, default) for key in keys]


@runtime_checkable
class IBackend(Protocol):
    """Protocol that provides backend access for query objects.

    This protocol defines a property for accessing the storage backend
    associated with a query object, which is necessary for consistent
    query execution across different database systems.
    """

    @property
    def backend(self) -> 'StorageBackend':
        """Get the storage backend for this query.

        Returns:
            StorageBackend: The backend instance for this query
        """
        ...


@runtime_checkable
class IQueryBuilding(Protocol):
    """Protocol for query building operations.

    This protocol defines the basic query building methods (WHERE, SELECT, ORDER BY, etc.)
    without database access. It's designed to be mixed into query classes that need
    query construction capabilities.
    """

    # region Instance Attributes
    _backend: StorageBackend
    # Query clause attributes
    where_clause: Optional[WhereClause]
    order_by_clause: Optional[OrderByClause]
    join_clauses: List[Union[str, type]]
    select_columns: Optional[List[BaseExpression]]
    limit_offset_clause: Optional[LimitOffsetClause]
    group_by_having_clause: Optional[GroupByHavingClause]
    _adapt_params: bool
    _explain_enabled: bool
    _explain_options: dict
    # endregion

    @overload
    def where(self, condition: str, params: Optional[Union[tuple, List[Any]]] = None) -> 'IQueryBuilding':
        """Add AND condition to the query using a SQL placeholder string."""
        ...

    @overload
    def where(self, condition: SQLPredicate, params: None = None) -> 'IQueryBuilding':
        """Add AND condition to the query using a predicate expression."""
        ...

    def where(self, condition, params=None):
        """Add AND condition to the query."""
        pass

    def select(self, *columns: Union[str, BaseExpression], append: bool = False) -> 'IQueryBuilding':
        """Select specific columns or expressions to retrieve from the query."""
        pass

    def order_by(self, *clauses: Union[str, BaseExpression, Tuple[Union[BaseExpression, str], str]]) -> 'IQueryBuilding':
        """Add ORDER BY clauses to the query."""
        pass

    def limit(self, count: Union[int, BaseExpression]) -> 'IQueryBuilding':
        """Add LIMIT clause to restrict the number of rows returned."""
        pass

    def offset(self, count: Union[int, BaseExpression]) -> 'IQueryBuilding':
        """Add OFFSET clause to skip a specified number of rows."""
        pass

    def group_by(self, *columns: Union[str, BaseExpression]) -> 'IQueryBuilding':
        """Add GROUP BY columns for complex aggregations."""
        pass

    @overload
    def having(self, condition: str, params: Optional[Union[tuple, List[Any]]] = None) -> 'IQueryBuilding':
        """Add HAVING condition using a SQL placeholder string for complex aggregations."""
        ...

    @overload
    def having(self, condition: SQLPredicate, params: None = None) -> 'IQueryBuilding':
        """Add HAVING condition using a predicate expression for complex aggregations."""
        ...

    def having(self, condition, params=None) -> 'IQueryBuilding':
        """Add HAVING condition for complex aggregations."""
        pass

    def explain(self, **kwargs) -> 'IQueryBuilding':
        """Enable EXPLAIN for the subsequent query execution."""
        pass


class IQuery(IBackend, ToSQLProtocol, ABC):
    """Basic interface for query objects.

    This interface defines the minimal contract for query objects,
    including backend access and SQL generation.
    """

    _backend: StorageBackend

    def __init__(self, backend: StorageBackend):
        super().__init__()
        self._backend = backend

    @abstractmethod
    def to_sql(self) -> Tuple[str, tuple]:
        """Get complete SQL query with parameters.

        This method returns the full SQL statement with parameter values
        ready for execution, following the ToSQLProtocol from the expression system.

        Returns:
            Tuple of (sql_query, params) where:
            - sql_query: Complete SQL string with placeholders
            - params: Tuple of parameter values

        Examples:
            sql, params = User.query().where('status = ?', (1,)).to_sql()
            print(f"SQL: {sql}")
            print(f"Params: {params}")
        """
        pass


# Define specialized interfaces for different query types
class IActiveQuery(IQuery, IQueryBuilding):
    """Interface for model-based queries that return ActiveRecord instances.

    This interface extends the general IQuery interface with model-specific
    functionality, including the model_class attribute and methods that
    return model instances instead of raw dictionaries.
    """

    model_class: Type['IActiveRecord']

    @abstractmethod
    def all(self) -> List['IActiveRecord']:
        """Execute query and return all matching records as model instances.

        Returns:
            List[IActiveRecord]: List of model instances (empty if no matches)
        """
        pass

    @abstractmethod
    def one(self) -> Optional['IActiveRecord']:
        """Execute query and return the first matching record as a model instance.

        Returns:
            Optional[IActiveRecord]: Single model instance or None
        """
        pass


class ICTEQuery(IQuery, IQueryBuilding):
    """Interface for Common Table Expression queries.

    CTE queries return raw data as dictionaries, not model instances.
    """


class ISetOperationQuery(IQuery):
    """Interface for set operation queries (UNION, INTERSECT, EXCEPT).

    This interface defines methods for performing set operations between queries.
    Classes implementing this interface should support chaining set operations
    and provide operator overloading for more Pythonic syntax.
    """

    @abstractmethod
    def union(self, other: Union['ISetOperationQuery', 'IQuery']) -> 'ISetOperationQuery':
        """Perform a UNION operation with another query.

        Args:
            other: Another query object (either ISetOperationQuery or IQuery)

        Returns:
            A new ISetOperationQuery instance representing the UNION
        """
        ...

    @abstractmethod
    def intersect(self, other: Union['ISetOperationQuery', 'IQuery']) -> 'ISetOperationQuery':
        """Perform an INTERSECT operation with another query.

        Args:
            other: Another query object (either ISetOperationQuery or IQuery)

        Returns:
            A new ISetOperationQuery instance representing the INTERSECT
        """
        ...

    @abstractmethod
    def except_(self, other: Union['ISetOperationQuery', 'IQuery']) -> 'ISetOperationQuery':
        """Perform an EXCEPT operation with another query.

        Args:
            other: Another query object (either ISetOperationQuery or IQuery)

        Returns:
            A new ISetOperationQuery instance representing the EXCEPT
        """
        ...

    def __or__(self, other: Union['ISetOperationQuery', 'IQuery']) -> 'ISetOperationQuery':
        """Implement the | operator for UNION."""
        return self.union(other)

    def __and__(self, other: Union['ISetOperationQuery', 'IQuery']) -> 'ISetOperationQuery':
        """Implement the & operator for INTERSECT."""
        return self.intersect(other)

    def __sub__(self, other: Union['ISetOperationQuery', 'IQuery']) -> 'ISetOperationQuery':
        """Implement the - operator for EXCEPT."""
        return self.except_(other)
