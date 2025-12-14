# src/rhosocial/activerecord/backend/expression.py
"""
Core definitions for SQL expression building blocks, including the base
SQLExpression class and literal value representation.
"""
from __future__ import annotations

import abc
from typing import Any, Tuple, Union, List, Generic, TypeVar, Optional, Dict

from .dialect import SQLDialectBase

T = TypeVar("T")

# --- Base Classes ---

class SQLExpression(abc.ABC):
    """
    Abstract base class for any part of a SQL expression. Its main purpose is
    to be converted into a SQL string and a tuple of parameters via `to_sql`.
    """

    @abc.abstractmethod
    def to_sql(self, dialect: SQLDialectBase) -> Tuple[str, tuple]:
        """
        Converts the expression into a SQL string and a tuple of parameters.
        """
        raise NotImplementedError

    def __and__(self, other: SQLExpression) -> "SQLOperation":
        return SQLOperation(self, "AND", other)

    def __or__(self, other: SQLExpression) -> "SQLOperation":
        return SQLOperation(self, "OR", other)

    def __invert__(self) -> "SQLOperation":
        return SQLOperation(self, "NOT", is_unary=True, unary_pos='before')

    def _operate(self, op: str, other: Any) -> "SQLOperation":
        other_expr = other if isinstance(other, SQLExpression) else Literal(other)
        return SQLOperation(self, op, other_expr)
    
    def __eq__(self, other: Any) -> "SQLOperation": return self._operate("=", other)
    def __ne__(self, other: Any) -> "SQLOperation": return self._operate("!=", other)
    def __gt__(self, other: Any) -> "SQLOperation": return self._operate(">", other)
    def __ge__(self, other: Any) -> "SQLOperation": return self._operate(">=", other)
    def __lt__(self, other: Any) -> "SQLOperation": return self._operate("<", other)
    def __le__(self, other: Any) -> "SQLOperation": return self._operate("<=", other)
    def __add__(self, other: Any) -> "SQLOperation": return self._operate("+", other)
    def __sub__(self, other: Any) -> "SQLOperation": return self._operate("-", other)
    def __mul__(self, other: Any) -> "SQLOperation": return self._operate("*", other)
    def __truediv__(self, other: Any) -> "SQLOperation": return self._operate("/", other)
    def __mod__(self, other: Any) -> "SQLOperation": return self._operate("%", other)

    def like(self, other: str) -> "SQLOperation": return self._operate("LIKE", other)
    def ilike(self, other: str) -> "SQLOperation": return self._operate("ILIKE", other)
    def in_(self, values: list) -> "SQLOperation":
        return SQLOperation(self, "IN", Literal(tuple(values)))
    def not_in(self, values: list) -> "SQLOperation":
        return SQLOperation(self, "NOT IN", Literal(tuple(values)))
    def between(self, low: Any, high: Any) -> "SQLOperation":
        return SQLOperation(self, "BETWEEN", SQLOperation(Literal(low), "AND", Literal(high)))
    def is_null(self) -> "SQLOperation": return SQLOperation(self, "IS NULL", is_unary=True, unary_pos='after')
    def is_not_null(self) -> "SQLOperation": return SQLOperation(self, "IS NOT NULL", is_unary=True, unary_pos='after')

class Literal(SQLExpression, Generic[T]):
    """Represents a literal value in a SQL query."""
    def __init__(self, value: T): self.value = value
    def to_sql(self, dialect: SQLDialectBase) -> Tuple[str, tuple]:
        if isinstance(self.value, (list, tuple, set)):
            if not self.value: return "()", ()
            return f"({', '.join([dialect.get_placeholder()] * len(self.value))})", tuple(self.value)
        return dialect.get_placeholder(), (self.value,)
    def __repr__(self) -> str: return f"Literal({self.value!r})"



