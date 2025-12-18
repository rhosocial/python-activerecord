# src/rhosocial/activerecord/backend/expression_/bases.py
"""
Core abstract base classes for the SQL expression engine.

This module forms the foundation of the expression hierarchy and should
have no dependencies on other modules within the `expression` package
to prevent circular imports.
"""
import abc
from typing import Tuple, Protocol, TYPE_CHECKING

# if TYPE_CHECKING:
#     from ..dialect import SQLDialectBase


class ToSQLProtocol(Protocol):
    """
    Protocol for objects that can be converted into a SQL string and a tuple of parameters.
    """
    def to_sql(self) -> Tuple[str, tuple]:
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

    @abc.abstractmethod
    def to_sql(self) -> Tuple[str, tuple]:
        """
        Converts the expression into a SQL string and a tuple of parameters.
        """
        raise NotImplementedError


class SQLPredicate(BaseExpression):
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
