# src/rhosocial/activerecord/backend/result.py
"""
Defines common data structures and type hints for backend operations.

This file serves as a central place for core backend-related types,
focusing on query results to avoid circular imports.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum, auto
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar, Union

# Base type aliases
DatabaseValue = Union[str, int, float, bool, datetime, Decimal, bytes, None]
PythonValue = TypeVar("PythonValue")
T = TypeVar("T")


@dataclass
class QueryResult(Generic[T]):
    """Query result wrapper for DQL (SELECT) operations.

    This class wraps the result of a query execution, providing access to
    the returned data along with execution metadata.

    Attributes:
        data: The query result data. For DQL queries, this is a list of tuples
            where each tuple represents a row. For DML queries without RETURNING,
            this is typically None. The generic type T allows for typed results.
        affected_rows: Number of rows affected by the operation. For DQL queries,
            this represents the number of rows returned. For DML queries (INSERT,
            UPDATE, DELETE), this represents the number of rows modified.
        last_insert_id: For INSERT operations, the rowid of the last inserted row.
            None for non-INSERT operations or when not applicable.
        duration: Query execution time in seconds. Useful for performance monitoring
            and optimization.

    Example:
        >>> # DQL query result
        >>> result = backend.execute("SELECT * FROM users")
        >>> rows = result.data  # List of tuples
        >>> for row in rows:
        ...     print(row[0], row[1])  # Access columns by index

        >>> # DML query result
        >>> result = backend.execute("UPDATE users SET active = 1")
        >>> print(f"Updated {result.affected_rows} rows")

        >>> # INSERT with rowid
        >>> result = backend.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
        >>> print(f"Inserted row ID: {result.last_insert_id}")
    """

    data: Optional[T] = None
    affected_rows: int = 0
    last_insert_id: Optional[int] = None
    duration: float = 0.0


class BatchCommitMode(Enum):
    """Transaction commit mode for batch DML operations.

    Attributes:
        WHOLE: Execute all batches in a single transaction. If any batch fails,
            the entire operation is rolled back. This is the default mode
            and provides atomicity for the entire batch operation.
        PER_BATCH: Commit after each batch completes. This allows partial
            success if the operation is interrupted, but loses atomicity
            for the entire operation.
    """

    WHOLE = auto()
    PER_BATCH = auto()


@dataclass
class BatchDMLResult:
    """Result of a single batch in batch DML execution.

    This class represents the result of processing one batch of DML expressions
    in the execute_batch_dml() method.

    Attributes:
        results: List of QueryResult objects when returning_columns is specified
            and the backend supports RETURNING clause. Empty list otherwise.
        batch_index: Zero-based index of this batch in the overall execution.
        batch_size: Actual number of expressions processed in this batch.
        total_affected_rows: Total number of rows affected by this batch.
        duration: Time taken to execute this batch in seconds.
        has_returning: Whether this batch contains RETURNING data.

    Example:
        >>> # Batch DML with RETURNING
        >>> results = backend.execute_batch_dml(expressions, returning_columns=['id'])
        >>> for batch_result in results:
        ...     if batch_result.has_returning:
        ...         for qr in batch_result.results:
        ...             print(f"Row returned: {qr.data}")
    """

    results: List[QueryResult]
    batch_index: int
    batch_size: int
    total_affected_rows: int
    duration: float
    has_returning: bool


@dataclass
class BatchDQLResult:
    """Result of a single page in batch DQL execution.

    This class represents the result of fetching one page of data
    in the execute_batch_dql() method.

    Attributes:
        data: List of row dictionaries (after type adaptation and column mapping)
            for this page. Each dictionary maps column names to values.
        page_index: Zero-based index of this page in the overall result set.
        page_size: Actual number of rows in this page.
        has_more: Whether there are more pages available.
        duration: Time taken to fetch this page in seconds.

    Example:
        >>> # Batch DQL pagination
        >>> for page_result in backend.execute_batch_dql(query, page_size=100):
        ...     for row_dict in page_result.data:
        ...         print(f"User: {row_dict['name']}, Email: {row_dict['email']}")
        ...     if not page_result.has_more:
        ...         break
    """

    data: List[Dict[str, Any]]
    page_index: int
    page_size: int
    has_more: bool
    duration: float
