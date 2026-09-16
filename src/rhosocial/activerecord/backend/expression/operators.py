# src/rhosocial/activerecord/backend/expression/operators.py
"""
SQL operations like binary, unary, and arithmetic expressions.

Every class here is a pure tree node: it declares its dialect formatting
method and holds construction parameters. Rendering is centralized in
``BaseExpression.to_sql()``, which re-instantiates the node, propagates the
dialect through the subtree, and hands it to the declared formatter.
"""

from typing import Any, Optional, Tuple, List, TYPE_CHECKING
from .bases import BaseExpression, SQLPredicate, SQLQueryAndParams, SQLValueExpression
from .mixins import (
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringMixin,
    TypeCastingMixin,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class SQLOperation(BaseExpression):
    """Represents a generic SQL operation."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_sql_operation"

    def __init__(self, dialect: "SQLDialectBase", op: str, *operands: "BaseExpression"):
        super().__init__(dialect)
        self.op = op
        self.operands = list(operands)


class BinaryExpression(BaseExpression):
    """Represents a binary SQL operation."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_binary_operator"

    def __init__(self, dialect: "SQLDialectBase", op: str, left: "BaseExpression", right: "BaseExpression"):
        super().__init__(dialect)
        self.op = op
        self.left = left
        self.right = right


class UnaryExpression(BaseExpression):
    """Represents a unary SQL operation."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_unary_operator"

    def __init__(self, dialect: "SQLDialectBase", op: str, operand: "BaseExpression", pos: str = "before"):
        super().__init__(dialect)
        self.op = op
        self.operand = operand
        self.pos = pos


class RawSQLExpression(ArithmeticMixin, ComparisonMixin, StringMixin, SQLValueExpression):
    """Represents a raw SQL expression string that is directly embedded.

    Note: This class should be used with caution. It bypasses the normal expression
    building mechanism and directly embeds raw SQL. This can lead to SQL injection
    vulnerabilities if user input is not properly sanitized. It should only be used
    when the expression is completely trusted or properly validated.

    Difference from RawSQLPredicate:
    - RawSQLExpression inherits from SQLValueExpression and represents a value expression
      (e.g., column, function call, literal)
    - RawSQLPredicate inherits from SQLPredicate and represents a boolean predicate
      (e.g., condition in WHERE clause)
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_raw_sql"

    def __init__(self, dialect: "SQLDialectBase", expression: str, params: tuple = ()):
        super().__init__(dialect)
        self.expression = expression
        self.params = tuple(params) if params else ()


class RawSQLPredicate(SQLPredicate):
    """Represents a raw SQL predicate string that is directly embedded as a predicate.

    Note: This class should be used with caution. It bypasses the normal expression
    building mechanism and directly embeds raw SQL. This can lead to SQL injection
    vulnerabilities if user input is not properly sanitized. It should only be used
    when the predicate is completely trusted or properly validated.

    Difference from RawSQLExpression:
    - RawSQLExpression inherits from SQLValueExpression and represents a value expression
      (e.g., column, function call, literal)
    - RawSQLPredicate inherits from SQLPredicate and represents a boolean predicate
      (e.g., condition in WHERE clause)
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_raw_sql"

    def __init__(self, dialect: "SQLDialectBase", expression: str, params: tuple = ()):
        super().__init__(dialect)
        self.expression = expression
        self.params = tuple(params) if params else ()


class BinaryArithmeticExpression(
    AliasableMixin, ArithmeticMixin, ComparisonMixin, TypeCastingMixin, SQLValueExpression
):
    """Represents a binary arithmetic operation."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_binary_arithmetic_expression"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        op: str,
        left: "SQLValueExpression",
        right: "SQLValueExpression",
        *,
        alias: "Optional[str]" = None,
    ):
        super().__init__(dialect)
        self.op = op
        self.left = left
        self.right = right
        self.alias = alias

    # Operator precedence levels for arithmetic operations (lower number
    # means lower precedence). The formatting function reads this map from
    # the expression class to decide parenthesization.
    OPERATOR_PRECEDENCE = {
        "+": 9,
        "-": 9,  # Addition and subtraction
        "*": 10,
        "/": 10,
        "%": 10,  # Multiplication, division, modulo
    }
