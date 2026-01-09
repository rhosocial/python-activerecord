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
from ..backend.dialect import SQLDialectBase
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
class IDialect(Protocol):
    """Protocol that provides dialect access for query objects.

    This protocol defines a property for accessing the SQL dialect
    associated with a query object, which is necessary for consistent
    SQL generation across different database backends.
    """

    @property
    def dialect(self) -> 'SQLDialectBase':
        """Get the SQL dialect for this query.

        Returns:
            SQLDialectBase: The dialect instance for this query's backend
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


class IQuery(IDialect, IQueryBuilding, ToSQLProtocol, ABC):
    """Interface for building and executing database queries.

    Provides a fluent interface for constructing SQL queries with:
    - Conditions (WHERE clauses)
    - Sorting (ORDER BY)
    - Grouping (GROUP BY)
    - Joins
    - Pagination (LIMIT/OFFSET)

    This is a general-purpose query interface that can be used for both
    model-based queries and raw data queries.

    Inherits from ToSQLProtocol to ensure consistent SQL generation interface
    across all query components in the expression system.
    """

    _backend: StorageBackend

    def __init__(self, backend: StorageBackend):
        super().__init__()
        self._backend = backend

    @overload
    def where(self, condition: str, params: Optional[Union[tuple, List[Any]]] = None) -> 'IQuery':
        """Add AND condition to the query using a SQL placeholder string.

        This requires you to construct SQL condition fragments with question marks as
        placeholders for parameters, with actual parameters appearing in 'params' in
        the order of placeholders in the SQL.

        Note: User input must absolutely not be directly concatenated here, as it
        would create SQL injection security vulnerabilities.

        Both overloads can be chained together and will be combined into a unified
        WHERE clause with AND logic.

        Args:
            condition: A SQL placeholder string with parameters (e.g., "name = ? AND age > ?")
            params: Query parameters for the placeholders

        Returns:
            Query instance for method chaining
        """
        ...

    @overload
    def where(self, condition: SQLPredicate, params: None = None) -> 'IQuery':
        """Add AND condition to the query using a predicate expression.

        This requires you to provide a query predicate. Query predicates can be
        instantiated manually or generated by ActiveRecord field proxy column names,
        such as User.c.age > 25, User.c.name.like('%test%'), or User.c.status.in_([1, 2, 3]).

        Both overloads can be chained together and will be combined into a unified
        WHERE clause with AND logic.

        Args:
            condition: A predicate expression (e.g., User.c.age > 25, which is a SQLPredicate instance)
            params: Should be None when using predicate expressions

        Returns:
            Query instance for method chaining
        """
        ...

    @abstractmethod
    def where(self, condition, params=None):
        """Add AND condition to the query.

        Args:
            condition: Condition expression. Can be:
                      1. A predicate expression (e.g., User.c.age > 25, which is a SQLPredicate instance)
                      2. A SQL placeholder string with parameters (e.g., "name = ? AND age > ?")
            params: Query parameters for placeholder strings (not used with expression objects)

        Returns:
            Query instance for method chaining

        Examples:
            1. Using ActiveRecord field proxy (recommended)
            User.query().where(User.c.status == 'active')
            User.query().where(User.c.age >= 18)
            User.query().where(User.c.name.like('%john%'))

            2. Using complex expressions with ActiveRecord field proxy
            User.query().where((User.c.age >= 18) & (User.c.status == 'active'))
            User.query().where(User.c.created_at >= datetime.now() - timedelta(days=30))

            3. Using raw SQL string with parameters (use with caution)
            # Warning: When using raw SQL strings, you must ensure the query is safe from SQL injection
            User.query().where('status = ?', ('active',))
            User.query().where('age >= ? AND status = ?', (18, 'active'))

        See overloaded method signatures for parameter details.
        """
        pass

    @abstractmethod
    def select(self, *columns: Union[str, BaseExpression], append: bool = False) -> 'IQuery':
        """Select specific columns or expressions to retrieve from the query.

        This method accepts both column names (strings) and expression objects.

        Args:
            *columns: Variable number of column names (str) or expression objects (BaseExpression) to select
            append: If True, append columns to existing selection.
                   If False (default), replace existing selection.

        Returns:
            IQuery: Query instance for method chaining

        Examples:
            1. Using ActiveRecord field proxy (recommended)
            User.query().select(User.c.id, User.c.name, User.c.email)
            User.query().select(User.c.name).where(User.c.status == 'active')

            2. Using raw column names (use with caution)
            # Warning: When using raw column names as strings, ensure they match your database schema
            User.query().select('id', 'name', 'email')
            User.query().select('name').where('status = ?', ('active',))
        """
        pass

    @abstractmethod
    def order_by(self, *clauses: Union[str, BaseExpression, Tuple[Union[BaseExpression, str], str]]) -> 'IQuery':
        """Add ORDER BY clauses to the query.

        Args:
            *clauses: Variable number of ordering specifications. Each can be:

                     1. A column name as string (e.g., "name")
                     2. An expression object (e.g., User.c.name, which is a BaseExpression instance)
                     3. A tuple of (expression, direction) where direction is "ASC" or "DESC"

        Returns:
            Query instance for method chaining

        Note:
            Unlike WHERE or HAVING clauses, ORDER BY clauses typically do not contain
            parameter placeholders. The expressions used in ORDER BY are usually column
            names, functions, or other deterministic expressions that define sort order.
            Any parameters returned by expression.to_sql() are ignored in ORDER BY context.

        Examples:
            1. Using ActiveRecord field proxy (recommended)
            User.query().order_by(User.c.name)
            User.query().order_by(User.c.created_at, User.c.name)

            2. Using expression objects with direction
            User.query().order_by((User.c.name, "ASC"))
            User.query().order_by((User.c.created_at, "DESC"), (User.c.name, "ASC"))

            3. Using string column names (use with caution)
            # Warning: When using raw column names as strings, ensure they match your database schema
            User.query().order_by("name")
            User.query().order_by("created_at", "name")

            4. With direction specification using tuples
            User.query().order_by(("name", "ASC"))
            User.query().order_by(("created_at", "DESC"), ("name", "ASC"))

            5. Complex expressions
            User.query().order_by(functions.upper(User.c.name))
            User.query().order_by((functions.length(User.c.description), "DESC"))
        """
        pass

    @abstractmethod
    def limit(self, count: Union[int, BaseExpression]) -> 'IQuery':
        """Add LIMIT clause to restrict the number of rows returned.

        Args:
            count: Maximum number of rows to return, can be an integer or expression

        Returns:
            Query instance for method chaining
        """
        pass

    @abstractmethod
    def offset(self, count: Union[int, BaseExpression]) -> 'IQuery':
        """Add OFFSET clause to skip a specified number of rows.

        Args:
            count: Number of rows to skip, can be an integer or expression

        Returns:
            Query instance for method chaining
        """
        pass


    @abstractmethod
    def in_list(self, column: str, values: Union[List[Any], Tuple[Any, ...]],
                empty_result: bool = True) -> 'IQuery':
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
               empty_result: bool = False) -> 'IQuery':
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
    def between(self, column: str, start: Any, end: Any) -> 'IQuery':
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
    def not_between(self, column: str, start: Any, end: Any) -> 'IQuery':
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
    def like(self, column: str, pattern: str) -> 'IQuery':
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
    def not_like(self, column: str, pattern: str) -> 'IQuery':
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
    def is_null(self, column: str) -> 'IQuery':
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
    def is_not_null(self, column: str) -> 'IQuery':
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

    @abstractmethod
    def exists(self) -> bool:
        """Check if any matching records exist.

        This method executes a query to check if any records match the query conditions.
        It's more efficient than fetching all records when only existence matters.

        Note: Calling .explain() before .exists() has no effect. To get execution plans for existence queries,
        use .select() with .explain() and .aggregate() instead:
        User.query().select(functions.count(User.c.id).as_('total')).explain().aggregate()

        Returns:
            bool: True if at least one record matches, False otherwise

        Examples:
            1. Using ActiveRecord field proxy (recommended)
            if User.query().where(User.c.email == email).exists():
                print("User exists")
            else:
                print("User does not exist")

            2. Check with complex conditions
            has_active_admins = User.query()\
                .where(User.c.role == 'admin')\
                .where(User.c.status == 'active')\
                .exists()

            3. Using raw SQL string with parameters (use with caution)
            # Warning: When using raw SQL strings, you must ensure the query is safe from SQL injection
            if User.query().where('email = ?', (email,)).exists():
                print("User exists")
            else:
                print("User does not exist")
        """
        pass

    @abstractmethod
    def explain(self, **kwargs) -> 'IQuery':
        """Enable EXPLAIN for the subsequent query execution.

        This method configures the query to generate an execution plan when executed.
        The explain will be performed when calling execution methods like all(), one(),
        count(), etc.

        The explain() method can be called at any point after query() and before
        the final execution method (all/one/exists/count/etc.). It can also be called
        multiple times, with the last call taking effect.

        Args:
            **kwargs: EXPLAIN options. These will be passed to ExplainOptions.

        Returns:
            IQuery: Query instance for method chaining

        Examples:
            1. Basic explain
            User.query().explain().all()

            2. With analysis and JSON output
            User.query()\
                .explain(analyze=True, format=ExplainFormat.JSON)\
                .all()

            3. PostgreSQL specific options
            User.query()\
                .explain(buffers=True, settings=True)\
                .all()

            4. Configure explain for aggregate query
            plan = User.query()\
                .group_by(User.c.department)\
                .explain(format=ExplainFormat.TEXT)\
                .count(User.c.id)

            5. Explain can be called at any point before execution
            query = User.query().where(User.c.status == 'active')
            query.explain()  # Enable explain
            result = query.all()  # Will show execution plan

            6. Multiple explain calls (last one takes effect)
            User.query()\
                .where(User.c.status == 'active')\
                .explain(format=ExplainFormat.TEXT)\  # First explain call
                .explain(analyze=True)\               # Second call overrides first
                .all()                                # Will use analyze=True option
        """
        pass


# Define specialized interfaces for different query types
class IActiveQuery(IQuery):
    """Interface for model-based queries that return ActiveRecord instances.

    This interface extends the general IQuery interface with model-specific
    functionality, including the model_class attribute and methods that
    return model instances instead of raw dictionaries.
    """

    model_class: Type['IActiveRecord']

    def __init__(self, model_class: Type['IActiveRecord']):
        super().__init__(model_class.backend())

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


class ICTEQuery(IQuery):
    """Interface for Common Table Expression queries.

    CTE queries return raw data as dictionaries, not model instances.
    """

    def __init__(self, backend: StorageBackend):
        super().__init__(backend)


class ISetOperationQuery(IQuery):
    """Interface for set operation queries (UNION, INTERSECT, EXCEPT).

    This interface defines methods for performing set operations between queries.
    Classes implementing this interface should support chaining set operations
    and provide operator overloading for more Pythonic syntax.
    """

    def __init__(self, backend: StorageBackend):
        super().__init__(backend)

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
