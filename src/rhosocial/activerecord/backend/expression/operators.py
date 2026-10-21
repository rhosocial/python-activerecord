# src/rhosocial/activerecord/backend/expression/operators.py
"""
SQL operations like binary, unary, and arithmetic expressions.

Every class here is a pure tree node: it declares its dialect formatting
method and holds construction parameters. Rendering is centralized in
``BaseExpression.to_sql()``, which re-instantiates the node, propagates the
dialect through the subtree, and hands it to the declared formatter.
"""

from enum import Enum
from typing import TYPE_CHECKING
from .bases import BaseExpression, SQLPredicate, SQLQueryAndParams, SQLValue
from .core import Literal
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


class ConcatenationOperation(
    AliasableMixin,
    ComparisonMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    SQLValue,
):

    """String concatenation, stated as an intent rather than an operator.

    ``||`` is the SQL standard's concatenation operator and PostgreSQL,
    Oracle, Snowflake, Firebird and ClickHouse all read it that way. MySQL and
    MariaDB read it as logical OR unless the server runs with
    ``PIPES_AS_CONCAT``, and SQL Server reads it as logical OR outright, so
    emitting ``a || b`` there yields a boolean where a string was meant — a
    wrong answer rather than a syntax error, which is the worst kind.

    The intent lives on the node's kind (``concatenation_operation``), so the
    node carries no operator parameter at all: its only construction
    parameters are ``left`` and ``right``. Carrying the intent on the kind
    lets each dialect pick its own spelling:
    :meth:`format_concatenation_operation` emits ``a || b`` by default and
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

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_concatenation_operation"

    def __init__(
        self, dialect: "SQLDialectBase", left: "BaseExpression", right: "BaseExpression"
    ):
        super().__init__(dialect)
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


def _bind_values(dialect: "SQLDialectBase", params) -> tuple:
    """Bind values as :class:`~.core.Literal` nodes, one per placeholder.

    A raw value cannot survive a round-trip. ``b"\\x00"`` and ``""`` are the same
    thing on the wire, and only the value's *kind* tells them apart -- so the
    values a raw statement binds are the one place a non-JSON type is allowed,
    and they are allowed only because a node names what they are.

    The caller may pass the bare value or an already-built ``Literal``; both
    arrive as the same thing. Passing an empty sequence yields an empty tuple,
    so a statement with no placeholders has nothing to unwrap at render time.
    """
    return tuple(p if isinstance(p, Literal) else Literal(dialect, p)
                 for p in (params or ()))


class RawSQL(ArithmeticMixin, ComparisonMixin, StringPatternPredicateMixin, SQLValue):
    """Represents a raw SQL expression string that is directly embedded.

    This is the escape hatch, and the name dropped ``Expression`` on purpose:
    a raw string is not an expression the library can reason about, so the
    bare ``RawSQL`` says what it is -- text the caller vouched for.

    Note: This class should be used with caution. It bypasses the normal expression
    building mechanism and directly embeds raw SQL. This can lead to SQL injection
    vulnerabilities if user input is not properly sanitized. It should only be used
    when the expression is completely trusted or properly validated.

    Difference from RawSQLPredicate:
    - RawSQL inherits from SQLValue and represents a value expression
      (e.g., column, function call, literal)
    - RawSQLPredicate inherits from SQLPredicate and represents a boolean predicate
      (e.g., condition in WHERE clause)

    Not admitted to the framework's default registry. ``expression`` is text
    the caller vouched for and ``to_sql()`` emits it verbatim, so a reader that
    resolved ``raw_sql`` out of an untrusted artifact would rebuild a node whose
    SQL the artifact chose. A caller whose artifacts it trusts can register the
    class itself; see :attr:`~...bases.BaseExpression.REGISTER_BY_DEFAULT`.
    """

    REGISTER_BY_DEFAULT = False

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_raw_sql"

    def __init__(self, dialect: "SQLDialectBase", expression: str, params: tuple = ()):
        super().__init__(dialect)
        self.expression = expression
        self.params = _bind_values(dialect, params)


class RawSQLPredicate(SQLPredicate):
    """Represents a raw SQL predicate string that is directly embedded as a predicate.

    Note: This class should be used with caution. It bypasses the normal expression
    building mechanism and directly embeds raw SQL. This can lead to SQL injection
    vulnerabilities if user input is not properly sanitized. It should only be used
    when the predicate is completely trusted or properly validated.

    Difference from RawSQL:
    - RawSQL inherits from SQLValue and represents a value expression
      (e.g., column, function call, literal)
    - RawSQLPredicate inherits from SQLPredicate and represents a boolean predicate
      (e.g., condition in WHERE clause)

    Not admitted to the framework's default registry, for the same reason as
    :class:`RawSQL`: rebuilding this node from an artifact would let the
    artifact choose the predicate text. See
    :attr:`~...bases.BaseExpression.REGISTER_BY_DEFAULT`.
    """

    REGISTER_BY_DEFAULT = False

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_raw_sql"

    def __init__(self, dialect: "SQLDialectBase", expression: str, params: tuple = ()):
        super().__init__(dialect)
        self.expression = expression
        self.params = _bind_values(dialect, params)


class ArithmeticOperator(str, Enum):
    """The five binary arithmetic operations, as the wire word form.

    ``str`` so a member *is* the word it carries. :attr:`ArithmeticOperation.op`
    is one of these, and the character the rendered SQL writes is a per-member
    property -- a symbol in the artifact would pin one language's spelling into
    a language-neutral payload.
    """

    ADD = "add"
    SUB = "sub"
    MUL = "mul"
    DIV = "div"
    MOD = "mod"

    #: A member *is* the word it carries: str() and f-string interpolation must
    #: yield the value, not ``ClassName.MEMBER``, or the rendered SQL and the
    #: artifact would carry the Python spelling. ``(str, Enum)`` alone does not
    #: give that -- ``Enum.__str__`` wins -- so it is stated here once.
    __str__ = str.__str__

    @property
    def symbol(self) -> str:
        """The character the standard spelling writes. Never in the artifact."""
        return _ARITHMETIC_SYMBOLS[self]


#: Operation word -> the character the standard spelling writes.
_ARITHMETIC_SYMBOLS = {
    ArithmeticOperator.ADD: "+",
    ArithmeticOperator.SUB: "-",
    ArithmeticOperator.MUL: "*",
    ArithmeticOperator.DIV: "/",
    ArithmeticOperator.MOD: "%",
}


class ArithmeticOperation(
    AliasableMixin, ArithmeticMixin, NumericValueMixin, ComparisonMixin,
    TypeCastingMixin, SQLValue
):
    """A binary arithmetic operation: ``add`` / ``sub`` / ``mul`` / ``div`` / ``mod``.

    The node names the *operation*, and the kind follows the class name
    (``arithmetic_operation``). ``op`` carries the operation as a word, not as
    the character one backend's lexer writes: ``add``/``sub``/``mul``/``div``/
    ``mod`` are the wire forms, and the dialect formatter maps each word to
    the character the rendered SQL writes (:attr:`OPERATOR_SYMBOLS`). A symbol
    in the artifact would pin one language's spelling into a language-neutral
    payload; the word does not.

    The word set is closed and checked at construction — an unknown word is
    refused where it is written, not rendered into whatever the formatter
    falls back to.

    Parenthesization follows the operator-precedence table carried on this
    class (``OPERATOR_PRECEDENCE``), keyed by the same words.
    """

    #: The character each operation word writes. The formatter reads it from
    #: here; the artifact never sees it. Keyed by the enum, so a word that is
    #: not one of the five cannot reach the map.
    OPERATOR_SYMBOLS = {op: op.symbol for op in ArithmeticOperator}

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_arithmetic_operation"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        op: ArithmeticOperator,
        left: "SQLValue",
        right: "SQLValue",
    ):
        try:
            self.op = (
                ArithmeticOperator(op)
                if isinstance(op, ArithmeticOperator)
                else ArithmeticOperator(str(op).lower())
            )
        except ValueError:
            raise ValueError(
                f"unknown arithmetic operation {op!r}: the operation words are "
                f"{sorted(o.value for o in ArithmeticOperator)}"
            ) from None
        super().__init__(dialect)
        self.left = left
        self.right = right

    # Operator precedence levels for arithmetic operations (lower number
    # means lower precedence), keyed by the operation words. The formatting
    # function reads this map from the expression class to decide
    # parenthesization.
    OPERATOR_PRECEDENCE = {
        ArithmeticOperator.ADD: 9,
        ArithmeticOperator.SUB: 9,
        ArithmeticOperator.MUL: 10,
        ArithmeticOperator.DIV: 10,
        ArithmeticOperator.MOD: 10,
    }
