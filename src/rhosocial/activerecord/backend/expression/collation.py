# src/rhosocial/activerecord/backend/expression/collation.py
"""
Collation expression support for SQL value expressions.
"""

from enum import Enum
from typing import Optional, Union, TYPE_CHECKING

from .bases import SQLValue
from .mixins import (
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringPatternPredicateMixin,
    TypeCastingMixin,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class CollateFunction(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringPatternPredicateMixin,
    TypeCastingMixin,
    SQLValue,
):
    """Applies an explicit collation to a SQL value expression."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_collate_expression"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        expression: SQLValue,
        collation: Union[str, Enum],
        *,
        alias: Optional[str] = None,
        schema: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.expression = expression
        self.collation = collation
        self.alias: Optional[str] = alias
        # Schema-qualified COLLATE (`schema.collation`) is the only option
        # any backend reads, so it is a named parameter rather than an open
        # bag: a catch-all cannot be matched by name on read, cannot declare
        # its serialized range, and lets a mistyped option through silently.
        self.schema: Optional[str] = schema

    @property
    def collation_name(self) -> str:
        if isinstance(self.collation, Enum):
            return str(self.collation.value)
        return str(self.collation)


def collate(
    expression: SQLValue,
    collation: Union[str, Enum],
    schema: Optional[str] = None,
) -> CollateFunction:
    # Inherit the expression's binding state (construction-time; may be None
    # to defer binding), matching the operator-overload convention.
    return CollateFunction(expression._dialect, expression, collation, schema=schema)
