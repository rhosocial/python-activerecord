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
from .value_types import STRING
from .mixins import (
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    NumericValueMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
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


class StringConcatExpression(
    AliasableMixin,
    ComparisonMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    BinaryExpression,
):

    VALUE_FAMILY = STRING
    """String concatenation, stated as an intent rather than an operator.

    ``||`` is the SQL standard's concatenation operator and PostgreSQL,
    Oracle, Snowflake, Firebird and ClickHouse all read it that way. MySQL and
    MariaDB read it as logical OR unless the server runs with
    ``PIPES_AS_CONCAT``, and SQL Server reads it as logical OR outright, so
    emitting ``a || b`` there yields a boolean where a string was meant — a
    wrong answer rather than a syntax error, which is the worst kind.

    Carrying the intent on the node lets each dialect pick its own spelling:
    :meth:`format_string_concatenation` emits ``a || b`` by default and
    ``CONCAT(a, b)`` where ``||`` means something else. Passing a bare ``||``
    through :class:`BinaryExpression` cannot work, because the token alone does
    not say which of the two meanings was meant.

    This is not the path for logical OR. That goes through
    :class:`~...expression.predicates.LogicalPredicate`, which has its own
    formatter, so the two never meet.

    The result is a string, so it carries the string value surface and the
    chain continues: ``col.concat_using_operator(other).upper()`` is
    ``UPPER(col || other)``.
    """

    def __init__(
        self, dialect: "SQLDialectBase", left: "BaseExpression", right: "BaseExpression"
    ):
        super().__init__(dialect, "||", left, right)


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


class RawSQLExpression(ArithmeticMixin, ComparisonMixin, StringPatternPredicateMixin, SQLValueExpression):
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
    AliasableMixin, ArithmeticMixin, NumericValueMixin, ComparisonMixin,
    TypeCastingMixin, SQLValueExpression
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
