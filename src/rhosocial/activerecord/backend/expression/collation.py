# src/rhosocial/activerecord/backend/expression/collation.py
"""
Collation expression support for SQL value expressions.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union, TYPE_CHECKING

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

_COLLATION_PART_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$-]*$")
_UNSAFE_COLLATION_TOKENS = (";", "--", "/*", "*/", "#", "'", '"', "`", "[", "]")


@dataclass(frozen=True)
class CollationName:
    """Structured SQL collation name."""

    name: str
    schema: Optional[str] = None
    keyword: Optional[str] = None

    def __post_init__(self) -> None:
        if self.keyword is not None:
            self._validate_part(self.keyword, "keyword")
            if self.schema is not None:
                raise ValueError("Collation keyword cannot be schema-qualified")
            if self.name != self.keyword:
                raise ValueError("Collation keyword name must match keyword")
            return

        self._validate_part(self.name, "name")
        if self.schema is not None:
            self._validate_part(self.schema, "schema")

    @classmethod
    def from_value(cls, value: Union[str, Enum, "CollationName"]) -> "CollationName":
        if isinstance(value, CollationName):
            return value
        if isinstance(value, Enum):
            return cls(str(value.value))
        return cls(value)

    @classmethod
    def as_keyword(cls, keyword: str) -> "CollationName":
        return cls(keyword, keyword=keyword)

    @staticmethod
    def _validate_part(value: str, part_name: str) -> None:
        if not isinstance(value, str) or not value:
            raise ValueError(f"Collation {part_name} must be a non-empty string")
        if any(char.isspace() or ord(char) < 32 for char in value):
            raise ValueError(f"Unsafe collation {part_name}: {value!r}")
        if any(token in value for token in _UNSAFE_COLLATION_TOKENS):
            raise ValueError(f"Unsafe collation {part_name}: {value!r}")
        if not _COLLATION_PART_RE.fullmatch(value):
            raise ValueError(f"Unsafe collation {part_name}: {value!r}")


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
        collation: Union[str, Enum, CollationName],
    ):
        super().__init__(dialect)
        self.expression = expression
        self.collation = CollationName.from_value(collation)
        self.alias: Optional[str] = None

    def to_sql(self) -> SQLQueryAndParams:
        sql, params = self.dialect.format_collate_expression(self)

        for target_type in self._cast_types:
            sql, params = self.dialect.format_cast_expression(sql, target_type, params, None)

        if self.alias:
            sql = f"{sql} AS {self.dialect.format_identifier(self.alias)}"

        return sql, params


def collate(
    expression: SQLValueExpression,
    collation: Union[str, Enum, CollationName],
) -> CollateExpression:
    return CollateExpression(expression.dialect, expression, collation)
