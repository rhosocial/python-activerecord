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

    def to_sql(self) -> SQLQueryAndParams:
        sql, params = self.dialect.format_collate_expression(self)

        for target_type in self._cast_types:
            sql, params = self.dialect.format_cast_expression(sql, target_type, params, None)

        if self.alias:
            sql = f"{sql} AS {self.dialect.format_identifier(self.alias)}"

        return sql, params


def collate(
    expression: SQLValueExpression,
    collation: Union[str, Enum],
    **collation_options: Any,
) -> CollateExpression:
    return CollateExpression(expression.dialect, expression, collation, **collation_options)
