# src/rhosocial/activerecord/backend/expression/predicates.py
"""
Concrete implementations of SQL predicate expressions (e.g., WHERE clause conditions).

Every class is a pure tree node: it declares its dialect formatting method
and holds construction parameters. Rendering is centralized in
``BaseExpression.to_sql()``.
"""

from typing import TYPE_CHECKING

from .bases import BaseExpression, SQLPredicate, SQLQueryAndParams

if TYPE_CHECKING:  # pragma: no cover
    from .bases import SQLValueExpression
    from ..dialect import SQLDialectBase


class ComparisonPredicate(SQLPredicate):
    """Represents a comparison predicate (e.g., expr1 = expr2, expr1 > expr2)."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_comparison_predicate"

    def __init__(self, dialect: "SQLDialectBase", op: str, left: "SQLValueExpression", right: "SQLValueExpression"):
        super().__init__(dialect)
        self.op = op
        self.left = left
        self.right = right


class LogicalPredicate(SQLPredicate):
    """Represents a logical predicate (e.g., pred1 AND pred2, NOT pred)."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_logical_predicate"

    def __init__(self, dialect: "SQLDialectBase", op: str, *predicates: "SQLPredicate"):
        super().__init__(dialect)
        self.op = op
        self.predicates = list(predicates)


class LikePredicate(SQLPredicate):
    """Represents a LIKE or ILIKE predicate."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_like_predicate"

    def __init__(self, dialect: "SQLDialectBase", op: str, expr: "SQLValueExpression", pattern: "SQLValueExpression"):
        super().__init__(dialect)
        self.op = op
        self.expr = expr
        self.pattern = pattern


class InPredicate(SQLPredicate):
    """Represents an IN predicate (e.g., expr IN (val1, val2) or expr IN (subquery))."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_in_predicate"

    def __init__(self, dialect: "SQLDialectBase", expr: "SQLValueExpression", values: "BaseExpression"):
        super().__init__(dialect)
        self.expr = expr
        self.values = values


class BetweenPredicate(SQLPredicate):
    """Represents a BETWEEN predicate (e.g., expr BETWEEN low AND high)."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_between_predicate"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        expr: "BaseExpression",
        low: "BaseExpression",
        high: "BaseExpression",
    ):
        super().__init__(dialect)
        self.expr = expr
        self.low = low
        self.high = high


class IsNullPredicate(SQLPredicate):
    """Represents an IS NULL or IS NOT NULL predicate.

    This predicate is implemented as a separate method (is_null()/is_not_null())
    rather than using Python's ``is`` operator because:

    1. Python's ``is`` operator cannot be overloaded - it always performs
       identity comparison (checking if two variables reference the same object).
    2. ``is`` is a keyword in Python, not a method name, so it cannot be
       used as a method name on expression objects.
    3. SQL's ``IS NULL`` has different semantics from Python's ``is None`` -
       SQL uses three-valued logic (TRUE, FALSE, NULL), while Python's ``is``
       checks object identity.

    Therefore, we provide ``is_null()`` and ``is_not_null()`` methods in
    ComparisonMixin to enable intuitive SQL IS NULL predicate generation.

    Example:
        >>> col = Column(dialect, "email")
        >>> col.is_null().to_sql()
        ('"email" IS NULL', ())
        >>> col.is_not_null().to_sql()
        ('"email" IS NOT NULL', ())
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_is_null_predicate"

    def __init__(self, dialect: "SQLDialectBase", expr: "BaseExpression", is_not: bool = False):
        super().__init__(dialect)
        self.expr = expr
        self.is_not = is_not


class IsBooleanPredicate(SQLPredicate):
    """Represents an IS TRUE, IS NOT TRUE, IS FALSE, or IS NOT FALSE predicate.

    This predicate is used for proper boolean comparisons in SQL, handling
    NULL values correctly. Unlike direct equality comparisons (= TRUE or = FALSE),
    IS TRUE/FALSE properly handles NULL values:

    - IS TRUE: matches only TRUE values (not FALSE or NULL)
    - IS NOT TRUE: matches FALSE and NULL values
    - IS FALSE: matches only FALSE values (not TRUE or NULL)
    - IS NOT FALSE: matches TRUE and NULL values

    This predicate is implemented as separate methods (is_true(), is_not_true(),
    is_false(), is_not_false()) rather than using Python's ``is`` operator because:

    1. Python's ``is`` operator cannot be overloaded - it always performs
       identity comparison (checking if two variables reference the same object).
    2. ``is`` is a keyword in Python, not a method name, so it cannot be
       used as a method name on expression objects.
    3. SQL's ``IS TRUE/FALSE`` has different semantics from Python's ``is
       True/False`` - SQL uses three-valued logic (TRUE, FALSE, NULL), while
       Python's ``is`` checks object identity.

    Example:
        >>> col = Column(dialect, "is_active")
        >>> col.is_true().to_sql()
        ('"is_active" IS TRUE', ())
        >>> col.is_not_true().to_sql()
        ('"is_active" IS NOT TRUE', ())
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_is_boolean_predicate"

    def __init__(self, dialect: "SQLDialectBase", expr: "BaseExpression", value: bool, is_not: bool = False):
        """
        Initialize an IS TRUE/FALSE predicate.

        Args:
            dialect: The SQL dialect to use for formatting
            expr: The expression to test
            value: True for IS TRUE/FALSE, False for IS FALSE/TRUE
            is_not: True for IS NOT TRUE/FALSE, False for IS TRUE/FALSE
        """
        super().__init__(dialect)
        self.expr = expr
        self.value = value
        self.is_not = is_not
