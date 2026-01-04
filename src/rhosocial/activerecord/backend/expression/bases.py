# src/rhosocial/activerecord/backend/expression/bases.py
"""
Core abstract base classes for the SQL expression engine.

This module forms the foundation of the expression hierarchy and should
have no dependencies on other modules within the `expression` package
to prevent circular imports.
"""
import abc
from typing import Tuple, Protocol, TYPE_CHECKING

from . import mixins

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class ToSQLProtocol(Protocol):
    """
    Protocol for objects that can be converted into a SQL string and a tuple of parameters.

    Security Notice:
    1. For backend developers: Any code involving database interfaces or SQL formatting
       must strictly follow this protocol by separating SQL fragments and parameters
       to prevent SQL injection attacks.
    2. For application developers: When interacting with the database, always pass
       query parameters through the designated parameter mechanisms rather than
       directly concatenating values into SQL strings to prevent SQL injection.
    """
    def to_sql(self) -> Tuple[str, tuple]: # pragma: no cover
        """
        Converts the object into a SQL string and a tuple of parameters.
        """
        ...


class BaseExpression(abc.ABC, ToSQLProtocol):
    """
    Abstract base class for any part of a SQL expression.
    """
    def __init__(self, dialect: "SQLDialectBase"):
        """
        Initializes the base SQL expression with a specific dialect.
        """
        self._dialect = dialect

    @property
    def dialect(self) -> "SQLDialectBase":
        return self._dialect

    def validate(self, strict: bool = True) -> None:
        """Validate expression parameters according to SQL standard.

        The correct usage of this function is to catch whether it raises an error.
        If no error is raised, it indicates that the validation has passed.
        Users can use this to quickly determine if the input parameters are appropriate.
        The error type is generally TypeError, but we do not enforce this,
        so users should be aware of all possible error types.

        Args:
            strict: If True, perform strict validation that may impact performance.
                   If False, skip validation for performance optimization.

        Raises:
            Exception: Subclasses may raise various exceptions to indicate validation failure
        """
        pass  # pragma: no cover

    @abc.abstractmethod
    def to_sql(self) -> Tuple[str, tuple]: # pragma: no cover
        """
        Converts the expression into a SQL string and a tuple of parameters.
        """
        raise NotImplementedError


class SQLPredicate(mixins.LogicalMixin, BaseExpression):
    """
    Abstract base class for SQL expressions that return a boolean value (predicates).
    """
    pass


class SQLValueExpression(BaseExpression):
    """
    Abstract base class for SQL expressions that return a non-boolean value
    (e.g., integer, string, date).
    """
    pass
