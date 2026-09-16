# src/rhosocial/activerecord/backend/expression/collation.py
"""
Collation expression support for SQL value expressions.
"""

from enum import Enum
from typing import Any, Dict, Optional, Union, TYPE_CHECKING

from .bases import SQLQueryAndParams, SQLValueExpression
from .mixins import (
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringMixin,
    TypeCastingMixin,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class CollateExpression(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """Applies an explicit collation to a SQL value expression."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_collate_expression"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        expression: SQLValueExpression,
        collation: Union[str, Enum],
        *,
        alias: Optional[str] = None,
        **collation_options: Any,
    ):
        super().__init__(dialect)
        self.expression = expression
        self.collation = collation
        self.alias: Optional[str] = alias
        self.collation_options: Dict[str, Any] = dict(collation_options)

    @property
    def collation_name(self) -> str:
        if isinstance(self.collation, Enum):
            return str(self.collation.value)
        return str(self.collation)


def collate(
    expression: SQLValueExpression,
    collation: Union[str, Enum],
    **collation_options: Any,
) -> CollateExpression:
    # Inherit the expression's binding state (construction-time; may be None
    # to defer binding), matching the operator-overload convention.
    return CollateExpression(expression._dialect, expression, collation, **collation_options)
