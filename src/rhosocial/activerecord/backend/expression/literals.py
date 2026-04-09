# src/rhosocial/activerecord/backend/expression/literals.py
"""
Literal identifiers in SQL expressions.
"""

from typing import TYPE_CHECKING
from .bases import SQLQueryAndParams, SQLValueExpression
from .mixins import ComparisonMixin

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class Identifier(ComparisonMixin, SQLValueExpression):
    """
    Represents a generic SQL identifier (e.g., table name, column name, alias).
    It is comparable but generally not used in arithmetic.
    """

    def __init__(self, dialect: "SQLDialectBase", name: str):
        super().__init__(dialect)
        self.name = name

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_identifier(self.name), ()

    def __repr__(self) -> str:
        return f"Identifier({self.name!r})"
