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
    """
    A thread-safe dictionary implementation using thread-local storage.

    This class provides a dictionary-like interface that maintains separate data
    for each thread, ensuring thread safety by isolating data per thread.
    Each thread gets its own copy of the data, so changes in one thread
    don't affect other threads.

    Note: This is not a shared thread-safe dictionary but rather a thread-isolated
    dictionary where each thread has its own instance of the data.
    """

    def __init__(self, *args, **kwargs):
        """Initialize thread-safe dictionary.

        Supports same initialization as dict:
        - Empty: ThreadSafeDict()
        - From mapping: ThreadSafeDict({'a': 1})
        - From iterable: ThreadSafeDict([('a', 1), ('b', 2)])
        - From kwargs: ThreadSafeDict(a=1, b=2)
        """
        # Initialize the thread-local storage
        self._local = local()
        # Call parent constructor with initial data
        super().__init__()
        # Store initial data in thread-local storage
        initial_data = {}
        if args:
            if len(args) > 1:
                raise TypeError('ThreadSafeDict expected at most 1 argument, got %d' % len(args))
            arg = args[0]
            if hasattr(arg, 'items'):
                # Mapping-like object
                initial_data.update(arg)
            else:
                # Iterable of pairs
                for key, value in arg:
                    initial_data[key] = value
        initial_data.update(kwargs)
        self._local.data = initial_data

    def __ensure_data(self) -> dict:
        """Ensure thread-local data exists.

        Returns:
            dict: Thread-local dictionary for the current thread
        """
        if not hasattr(self._local, 'data'):
            self._local.data = {}
        return self._local.data

    def __getitem__(self, key: K) -> V:
        """Get item from thread-local storage."""
        return self.__ensure_data()[key]

    def __setitem__(self, key: K, value: V) -> None:
        """Set item in thread-local storage."""
        self.__ensure_data()[key] = value

    def __delitem__(self, key: K) -> None:
        """Delete item from thread-local storage."""
        del self.__ensure_data()[key]

    def __iter__(self) -> Iterator[K]:
        """Iterate over thread-local storage."""
        return iter(self.__ensure_data())

    def __len__(self) -> int:
        """Get length of thread-local storage."""
        return len(self.__ensure_data())

    def __contains__(self, key: K) -> bool:
        """Check if key exists in thread-local storage."""
        return key in self.__ensure_data()

    def __bool__(self) -> bool:
        """Check if thread-local storage is non-empty."""
        return bool(self.__ensure_data())

    def __eq__(self, other: object) -> bool:
        """Compare with another dict-like object."""
        if not isinstance(other, (dict, ThreadSafeDict)):
            return NotImplemented
        return self.__ensure_data() == dict(other)

    def __repr__(self) -> str:
        """String representation of the thread-local data."""
        return f"ThreadSafeDict({repr(self.__ensure_data())})"

    def __str__(self) -> str:
        """String representation of the thread-local data."""
        return str(self.__ensure_data())

    # Standard dict methods
    def clear(self) -> None:
        """Remove all items from the thread-local dictionary."""
        self.__ensure_data().clear()

    def copy(self) -> 'ThreadSafeDict[K, V]':
        """Return a shallow copy of the thread-local dictionary."""
        result = ThreadSafeDict()
        result._local.data = self.__ensure_data().copy()
        return result

    def get(self, key: K, default: Any = None) -> Optional[V]:
        """Return value for key if it exists, else default."""
        return self.__ensure_data().get(key, default)

    def items(self) -> ItemsView[K, V]:
        """Return a view of thread-local dictionary's items (key-value pairs)."""
        return self.__ensure_data().items()

    def keys(self) -> KeysView[K]:
        """Return a view of thread-local dictionary's keys."""
        return self.__ensure_data().keys()

    def values(self) -> ValuesView[V]:
        """Return a view of thread-local dictionary's values."""
        return self.__ensure_data().values()

    def pop(self, key: K, default: Any = ...) -> V:
        """Remove specified key and return the corresponding value from thread-local storage.

        If default is provided and key doesn't exist, return default.
        If default is not provided and key doesn't exist, raise KeyError.
        """
        data = self.__ensure_data()
        if default is ...:
            return data.pop(key)
        return data.pop(key, default)

    def popitem(self) -> Tuple[K, V]:
        """Remove and return an arbitrary (key, value) pair from thread-local storage.

        Raises:
            KeyError: If thread-local dictionary is empty
        """
        return self.__ensure_data().popitem()

    def setdefault(self, key: K, default: V = None) -> V:
        """Return value for key if it exists, else set and return default in thread-local storage."""
        return self.__ensure_data().setdefault(key, default)

    def update(self, *args, **kwargs) -> None:
        """Update thread-local dictionary with elements from args and kwargs.

        Args can be:
        - another dictionary
        - an iterable of key/value pairs
        - keyword arguments
        """
        data = self.__ensure_data()
        if args:
            if len(args) > 1:
                raise TypeError('update expected at most 1 argument, got %d' % len(args))
            other = args[0]
            if isinstance(other, Mapping):
                data.update(other)
            elif hasattr(other, 'keys'):
                data.update({k: other[k] for k in other.keys()})
            else:
                for key, value in other:
                    data[key] = value
        data.update(kwargs)

    # Additional useful methods
    def to_dict(self) -> Dict[K, V]:
        """Convert thread-local data to a regular dictionary."""
        return dict(self.__ensure_data())

    def set_many(self, items: List[Tuple[K, V]]) -> None:
        """Set multiple items at once from a list of tuples in thread-local storage."""
        data = self.__ensure_data()
        for key, value in items:
            data[key] = value

    def get_many(self, keys: List[K], default: Any = None) -> List[V]:
        """Get multiple values at once from thread-local storage.

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
    """
    Basic interface for query objects.

    This interface defines the minimal contract for query objects,
    including backend access and SQL generation. All query implementations
    should extend this interface to ensure consistent behavior across
    different query types and database backends.

    The interface combines:
    - IBackend: Provides access to the storage backend
    - ToSQLProtocol: Enables SQL generation functionality
    - ABC: Abstract base class for enforceable contracts
    """

    _backend: StorageBackend

    def __init__(self, backend: StorageBackend):
        """
        Initialize the query with a backend.

        Args:
            backend: The storage backend to use for query execution
        """
        super().__init__()
        self._backend = backend

    @abstractmethod
    def to_sql(self) -> Tuple[str, tuple]:
        """
        Generate the complete SQL query with parameters.

        This method returns the full SQL statement with parameter values
        ready for execution, following the ToSQLProtocol from the expression system.
        The parameters are returned separately to prevent SQL injection attacks
        and allow proper parameter binding by the database driver.

        Returns:
            Tuple[str, tuple]: A tuple containing:
            - sql_query: Complete SQL string with placeholders (usually '?')
            - params: Tuple of parameter values in the correct order

        Examples:
            >>> query = User.query().where(User.c.status == 'active')
            >>> sql, params = query.to_sql()
            >>> print(f"SQL: {sql}")
            >>> print(f"Params: {params}")
            SQL: SELECT * FROM users WHERE status = ?
            Params: ('active',)

        Note:
            The method should never return user data directly embedded in the SQL string,
            always use parameter placeholders to ensure security against SQL injection.
        """
        pass


# Define specialized interfaces for different query types
class IActiveQuery(IQuery, IQueryBuilding):
    """
    Interface for model-based queries that return ActiveRecord instances.

    This interface extends the general IQuery interface with model-specific
    functionality, including the model_class attribute and methods that
    return model instances instead of raw dictionaries.

    This interface is designed for queries that operate on ActiveRecord models
    and need to return properly instantiated model objects with all their
    methods and properties intact.
    """

    model_class: Type['IActiveRecord']
    """
    The model class that this query operates on and returns instances of.

    This attribute specifies which ActiveRecord model class the query is
    associated with. It's used internally to instantiate the correct model
    types when executing the query.
    """

    @abstractmethod
    def all(self) -> List['IActiveRecord']:
        """
        Execute the query and return all matching records as model instances.

        This method executes the query against the database and returns all
        matching records wrapped in instances of the appropriate ActiveRecord
        model class. Each returned instance will have full ActiveRecord
        functionality including change tracking, validation, and persistence methods.

        Returns:
            List[IActiveRecord]: List of model instances that match the query criteria.
                               Returns an empty list if no records match.

        Raises:
            DatabaseError: If there are issues connecting to or executing against
                          the database
            ValidationError: If there are issues instantiating model instances
                           from the database data

        Example:
            >>> users = User.query().where(User.c.status == 'active').all()
            >>> for user in users:
            ...     print(f"User: {user.username}")
        """
        pass

    @abstractmethod
    def one(self) -> Optional['IActiveRecord']:
        """
        Execute the query and return the first matching record as a model instance.

        This method executes the query against the database and returns the first
        matching record wrapped in an ActiveRecord model instance. If no matching
        record is found, it returns None.

        Unlike the 'first' method (if available), this method is intended to be
        used when exactly one result is expected (though None is acceptable).

        Returns:
            Optional[IActiveRecord]: Single model instance if a matching record is found,
                                   None if no records match

        Raises:
            DatabaseError: If there are issues connecting to or executing against
                          the database
            ValidationError: If there are issues instantiating the model instance
                           from the database data

        Example:
            >>> user = User.query().where(User.c.username == 'john').one()
            >>> if user:
            ...     print(f"Found user: {user.username}")
        """
        pass


class IAsyncActiveQuery(IQuery, IQueryBuilding):
    """Interface for asynchronous model-based queries that return ActiveRecord instances.

    This interface extends the general IQuery interface with model-specific
    functionality, including the model_class attribute and async methods that
    return model instances instead of raw dictionaries.
    """

    model_class: Type['IActiveRecord']

    @abstractmethod
    async def all(self) -> List['IActiveRecord']:
        """Execute query asynchronously and return all matching records as model instances.

        Returns:
            List[IActiveRecord]: List of model instances (empty if no matches)
        """
        pass

    @abstractmethod
    async def one(self) -> Optional['IActiveRecord']:
        """Execute query asynchronously and return the first matching record as a model instance.

        Returns:
            Optional[IActiveRecord]: Single model instance or None
        """
        pass


class ICTEQuery(IQuery, IQueryBuilding):
    """Interface for Common Table Expression queries.

    CTE queries return raw data as dictionaries, not model instances.
    """


class IAsyncCTEQuery(IQuery, IQueryBuilding):
    """Interface for asynchronous Common Table Expression queries.

    Async CTE queries return raw data as dictionaries, not model instances.
    """


class ISetOperationQuery(IQuery):
    """
    Interface for set operation queries (UNION, INTERSECT, EXCEPT).

    This interface defines methods for performing SQL set operations between queries.
    Set operations allow combining results from multiple queries in specific ways:
    - UNION: Combines results from both queries, removing duplicates
    - UNION ALL: Combines results from both queries, keeping duplicates
    - INTERSECT: Returns only rows that exist in both queries
    - EXCEPT/MINUS: Returns rows from the first query that don't exist in the second

    Classes implementing this interface should support chaining set operations
    and provide operator overloading for more Pythonic syntax.
    """

    @abstractmethod
    def union(self, other: Union['ISetOperationQuery', 'IQuery']) -> 'ISetOperationQuery':
        """
        Perform a UNION operation with another query, combining results and removing duplicates.

        The UNION operation combines the result sets of two queries, removing duplicate rows.
        Both queries must have the same number of columns with compatible data types.

        Args:
            other: Another query object (either ISetOperationQuery or IQuery) to union with

        Returns:
            ISetOperationQuery: A new query instance representing the UNION operation

        Example:
            >>> users_query = User.query().select(User.c.username)
            >>> admins_query = Admin.query().select(Admin.c.username)
            >>> combined = users_query.union(admins_query)
            >>> # Returns all unique usernames from both tables
        """
        ...

    @abstractmethod
    def intersect(self, other: Union['ISetOperationQuery', 'IQuery']) -> 'ISetOperationQuery':
        """
        Perform an INTERSECT operation with another query, returning only common rows.

        The INTERSECT operation returns only the rows that exist in both queries.
        Both queries must have the same number of columns with compatible data types.

        Args:
            other: Another query object (either ISetOperationQuery or IQuery) to intersect with

        Returns:
            ISetOperationQuery: A new query instance representing the INTERSECT operation

        Example:
            >>> active_users = User.query().where(User.c.status == 'active')
            >>> premium_users = User.query().where(User.c.plan == 'premium')
            >>> active_premium = active_users.intersect(premium_users)
            >>> # Returns users who are both active AND on premium plan
        """
        ...

    @abstractmethod
    def except_(self, other: Union['ISetOperationQuery', 'IQuery']) -> 'ISetOperationQuery':
        """
        Perform an EXCEPT operation with another query, returning rows from first query not in second.

        The EXCEPT operation returns rows from the first query that do not exist in the second query.
        Both queries must have the same number of columns with compatible data types.
        Note: This method is named 'except_' to avoid conflict with Python's 'except' keyword.

        Args:
            other: Another query object (either ISetOperationQuery or IQuery) to subtract

        Returns:
            ISetOperationQuery: A new query instance representing the EXCEPT operation

        Example:
            >>> all_users = User.query()
            >>> admin_users = User.query().where(User.c.role == 'admin')
            >>> non_admin_users = all_users.except_(admin_users)
            >>> # Returns all users who are not admins
        """
        ...

    def __or__(self, other: Union['ISetOperationQuery', 'IQuery']) -> 'ISetOperationQuery':
        """
        Implement the | operator for UNION operations.

        This enables Pythonic syntax for UNION operations: query1 | query2

        Args:
            other: Another query object to union with

        Returns:
            ISetOperationQuery: A new query instance representing the UNION operation
        """
        return self.union(other)

    def __and__(self, other: Union['ISetOperationQuery', 'IQuery']) -> 'ISetOperationQuery':
        """
        Implement the & operator for INTERSECT operations.

        This enables Pythonic syntax for INTERSECT operations: query1 & query2

        Args:
            other: Another query object to intersect with

        Returns:
            ISetOperationQuery: A new query instance representing the INTERSECT operation
        """
        return self.intersect(other)

    def __sub__(self, other: Union['ISetOperationQuery', 'IQuery']) -> 'ISetOperationQuery':
        """
        Implement the - operator for EXCEPT operations.

        This enables Pythonic syntax for EXCEPT operations: query1 - query2

        Args:
            other: Another query object to subtract

        Returns:
            ISetOperationQuery: A new query instance representing the EXCEPT operation
        """
        return self.except_(other)
