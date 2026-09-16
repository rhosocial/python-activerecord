# src/rhosocial/activerecord/backend/expression/literals.py
"""
Literal identifiers in SQL expressions.
"""

from typing import TYPE_CHECKING, Optional
from .bases import SQLQueryAndParams, SQLValueExpression
from .mixins import ComparisonMixin

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class Identifier(ComparisonMixin, SQLValueExpression):
    """Represents a generic SQL identifier (e.g., table name, column name, alias).

    Per-role quoting fields (all default to ``True``):
    - ``name_need_quote`` ↔ ``name``
    - ``alias_need_quote`` ↔ ``alias``
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        name_need_quote: bool = True,
        alias_need_quote: bool = True,
    ):
        super().__init__(dialect)
        self.name_need_quote = name_need_quote
        self.alias_need_quote = alias_need_quote
        self.name = name

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_identifier_expression"

    def __repr__(self) -> str:
        return f"Identifier({self.name!r})"


# Register Identifier in the expression registry for serialization support.
# This is done here rather than in serialization._auto_register_builtins
# to avoid circular import issues during module initialization.
from .serialization import ExpressionRegistry  # noqa: E402

ExpressionRegistry.register(Identifier)
