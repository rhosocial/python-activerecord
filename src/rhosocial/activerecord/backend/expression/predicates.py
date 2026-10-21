# src/rhosocial/activerecord/backend/expression/predicates.py
"""
Concrete implementations of SQL predicate expressions (e.g., WHERE clause conditions).

Every class is a pure tree node: it declares its dialect formatting method
and holds construction parameters. Rendering is centralized in
``BaseExpression.to_sql()``.
"""

from enum import Enum
from typing import TYPE_CHECKING, Any

from .bases import BaseExpression, SQLPredicate

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase
    from .bases import SQLValue


class ComparisonOperator(str, Enum):
    """The six comparison operations, as the wire word form.

    ``str`` so a member *is* the word it carries, and the character the rendered
    SQL writes is a per-member property. The symbol never reaches the artifact:
    it is a spelling, and the artifact has to be byte-identical across four
    languages that do not agree on it -- ``<>`` against ``ne``, ``!=`` against
    either. The word is what the languages can agree on; the symbol is what the
    dialect formatter owns.

    This is the same shape :class:`~.operators.ArithmeticOperator` already has.
    Comparison was the one family that still passed SQL characters, so its
    artifacts read as SQL rather than as expressions, and no other port could
    reproduce them.
    """

    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"

    #: A member *is* the word it carries: str() and f-string interpolation must
    #: yield the value, not ``ClassName.MEMBER``, or the artifact would carry
    #: the Python spelling. ``(str, Enum)`` alone does not give that --
    #: ``Enum.__str__`` wins -- so it is stated here once.
    __str__ = str.__str__

    @property
    def symbol(self) -> str:
        """The character the standard spelling writes. Never in the artifact."""
        return self.symbols()[self]

    @classmethod
    def symbols(cls) -> "dict[ComparisonOperator, str]":
        """Each operation, and the character the standard spelling writes.

        The table lives here rather than beside the class because it is the
        operator's own vocabulary: the word is the operation, and the character
        is one spelling of it.
        """
        return {
            cls.EQ: "=",
            cls.NE: "<>",
            cls.GT: ">",
            cls.GTE: ">=",
            cls.LT: "<",
            cls.LTE: "<=",
        }

    @classmethod
    def characters(cls) -> "dict[str, ComparisonOperator]":
        """The SQL characters a caller may still pass, and the word each means.

        A comparison written ``a >= b`` is the same comparison written
        ``a.gte(b)``, and accepting the character keeps every call site working
        while the artifact sees only the word. It is a constructor convenience,
        not a wire form: what :attr:`ComparisonPredicate.op` holds is always
        the enum.
        """
        return {
            "=": cls.EQ,
            "==": cls.EQ,
            "!=": cls.NE,
            "<>": cls.NE,
            ">": cls.GT,
            ">=": cls.GTE,
            "<": cls.LT,
            "<=": cls.LTE,
        }


class ComparisonPredicate(SQLPredicate):
    """Represents a comparison predicate (``left <op> right``).

    ``op`` is a :class:`ComparisonOperator`, so it names the operation rather
    than spelling it: ``gte`` travels, ``>=`` is written by the formatter. A
    caller may still pass the character -- see
    :meth:`coerce_operator` -- and the node ends up the same.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_comparison_predicate"

    @classmethod
    def coerce_operator(cls, op: Any) -> ComparisonOperator:
        """Resolve *op* to a :class:`ComparisonOperator`.

        Lives on this class because what it protects is this class's own input
        invariant: ``self.op`` is a member, and the code enforcing that belongs
        with the attribute it guards.

        Accepts a member, a wire word, or a SQL character, so a caller writing
        ``a >= b`` and one writing ``a.gte(b)`` build the same node. Anything
        else raises rather than passing through -- an operator this node cannot
        render would otherwise surface much later, as malformed SQL.
        """
        if isinstance(op, ComparisonOperator):
            return op
        text = str(op).strip()
        characters = ComparisonOperator.characters()
        if text in characters:
            return characters[text]
        try:
            return ComparisonOperator(text.lower())
        except ValueError:
            raise ValueError(
                f"unknown comparison operation {op!r}: the operation words are "
                f"{sorted(o.value for o in ComparisonOperator)}"
            ) from None

    def __init__(self, dialect: "SQLDialectBase", op: Any, left: "SQLValue", right: "SQLValue"):
        super().__init__(dialect)
        self.op = self.coerce_operator(op)
        self.left = left
        self.right = right


class LogicalPredicate(SQLPredicate):
    """Represents a logical predicate (e.g., pred1 AND pred2, NOT pred)."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_logical_predicate"

    def __init__(self, dialect: "SQLDialectBase", op: str, *operands: "SQLPredicate"):
        super().__init__(dialect)
        self.op = op
        self.operands = list(operands)


class LikeOperator(str, Enum):
    """The LIKE family's operations, as the wire word form.

    Same shape as :class:`ComparisonOperator`, and for the same reason: the word
    is what four languages agree on and what the artifact may carry; the SQL
    keyword is a spelling the dialect owns and the artifact never sees. LIKE was
    the family that still passed SQL text through the node -- which is how
    `not_like` ended up rendered as a SQL operator -- so it was the last one
    needing this split.

    ``ILIKE`` is a member even though :class:`ILikePredicate` exists, and that is
    deliberate: they are two different promises. ``ilike()`` writes the ``ILIKE``
    spelling and lets the backend accept it or refuse it -- the behaviour its
    callers and its tests already have. ``ILikePredicate`` is built explicitly
    and asks the dialect for a portable ``LOWER(x) LIKE LOWER(y)`` emulation.
    Routing one into the other silently rewrites SQL that callers depend on,
    so the two are kept apart.
    """

    LIKE = "like"
    NOT_LIKE = "not_like"
    ILIKE = "ilike"

    __str__ = str.__str__

    @property
    def keyword(self) -> str:
        """The keyword the standard spelling writes. Never in the artifact."""
        return self.keywords()[self]

    @classmethod
    def keywords(cls) -> "dict[LikeOperator, str]":
        """Each operation, and the keyword the standard spelling writes.

        The table lives here rather than beside the class because it is the
        operator's own vocabulary: the word is the operation, and the keyword is
        one spelling of it.
        """
        return {
            cls.LIKE: "LIKE",
            cls.NOT_LIKE: "NOT LIKE",
            cls.ILIKE: "ILIKE",
        }

    @classmethod
    def _missing_(cls, value: Any) -> "LikeOperator":
        """Accept the SQL keyword as well as the word.

        The enum knows both spellings -- the word it carries and the keyword the
        dialect writes -- so it can be built from either, and the keyword is
        coerced away on the way in so it never reaches the artifact. This is the
        same acceptance :meth:`~.predicates.ComparisonPredicate.coerce_operator` gives
        its family, where a caller may write ``">="`` and still get the word
        ``gte``.

        Python calls this only when the ordinary lookup fails, so a member
        found directly never routes through it.
        """
        text = str(value).strip()
        for member in cls:
            if member.value == text.lower():
                return member
        for member, keyword in cls.keywords().items():
            if keyword == text.upper():
                return member
        return None


class LikePredicate(SQLPredicate):
    """Represents a LIKE or ILIKE predicate."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_like_predicate"

    @classmethod
    def coerce_operator(cls, op: Any) -> "LikeOperator":
        """Resolve *op* to a :class:`LikeOperator`.

        Lives on this class rather than beside it as a free function, because
        what it protects is this class's own input invariant: ``self.op`` is a
        member, and the code that enforces that belongs with the class whose
        attribute it guards.

        Accepts a member, a wire word, or the SQL keyword, and raises rather
        than passing through an unknown one. This is the same contract
        :func:`~.predicates.normalize_comparison_operator` gives its family: a
        spelling may come in, it is coerced on the way in, and never reaches the
        artifact. The word/keyword split this class was built for is about what
        the artifact *carries*, not about what a caller is allowed to write --
        refusing the keyword would not protect the artifact, it would only break
        callers that spell it the way the rendered SQL reads.

        The raise exists so a typo fails where it is written rather than
        surfacing much later as an AttributeError from the renderer, which is
        what a caller passing the bare string ``"LIKE"`` used to get.
        """
        if isinstance(op, LikeOperator):
            return op
        text = str(op).strip()
        if not text:
            raise ValueError("a LIKE operator word is required")
        try:
            return LikeOperator(text)
        except ValueError:
            raise ValueError(
                f"unknown LIKE operator {op!r}; expected one of "
                f"{sorted(o.value for o in LikeOperator)}"
            ) from None

    def __init__(
        self,
        dialect: "SQLDialectBase",
        op: "LikeOperator",
        left: "SQLValue",
        pattern: "SQLValue",
    ):
        super().__init__(dialect)
        # Coerced here so a caller passing a word rather than a member still
        # gets one, and a caller passing a *keyword* fails at the call that
        # wrote it instead of in the renderer.
        self.op = self.coerce_operator(op)
        self.left = left
        self.pattern = pattern


class InPredicate(SQLPredicate):
    """Represents an IN predicate (e.g., expr IN (val1, val2) or expr IN (subquery))."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_in_predicate"

    def __init__(self, dialect: "SQLDialectBase", operand: "SQLValue", values: "BaseExpression"):
        super().__init__(dialect)
        self.operand = operand
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
        operand: "BaseExpression",
        low: "BaseExpression",
        high: "BaseExpression",
    ):
        super().__init__(dialect)
        self.operand = operand
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

    def __init__(self, dialect: "SQLDialectBase", operand: "BaseExpression", is_not: bool = False):
        super().__init__(dialect)
        self.operand = operand
        self.is_not = is_not


class ILikePredicate(SQLPredicate):
    """Represents a dialect-dispatched ILIKE (case-insensitive LIKE) predicate.

    Unlike :class:`LikePredicate` (which always renders through the generic
    ``format_like_predicate``), this node delegates to the dialect's
    ``format_ilike_predicate`` hook so a dialect can emit a native ``ILIKE``
    operator or a portable ``LOWER(...) LIKE LOWER(...)`` fallback.

    Attributes:
        column: Column name or expression with ``to_sql()``.
        pattern: Pattern string; compared case-insensitively.
        negate: If True, renders ``NOT LIKE`` instead of ``LIKE``.

    Example:
        >>> expr = ILikePredicate(dialect, Column(dialect, "name"), "John%")
        >>> expr.to_sql()
        ('LOWER("name") LIKE LOWER(?)', ('john%',))
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_ilike_predicate"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        column: Any,
        pattern: str,
        negate: bool = False,
    ):
        super().__init__(dialect)
        self.column = column
        self.pattern = pattern
        self.negate = negate


class DistinctFromPredicate(SQLPredicate):
    """Represents a NULL-safe ``IS [NOT] DISTINCT FROM`` comparison.

    ``a != b`` answers NULL when either side is NULL; this predicate asks the
    question that survives NULL -- "are these two different, NULL included" --
    which is what a caller filtering for "not equal" usually means. The
    spelling is a dialect matter (``IS NOT DISTINCT FROM`` is ``ORA-00908`` on
    Oracle, and SQL Server only learned it in 2022), so the node delegates to
    the dialect's ``format_distinct_from_predicate`` hook rather than
    hard-coding the SQL here.

    Attributes:
        left: Left operand with ``to_sql()``.
        right: Right operand with ``to_sql()``.
        is_not: If True, renders ``IS NOT DISTINCT FROM`` instead.

    Example:
        >>> expr = DistinctFromPredicate(dialect, Column(dialect, "age"), Literal(dialect, 0))
        >>> expr.to_sql()
        ('"age" IS DISTINCT FROM ?', (0,))
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_distinct_from_predicate"

    def __init__(self, dialect: "SQLDialectBase", left: Any, right: Any, is_not: bool = False):
        super().__init__(dialect)
        self.left = left
        self.right = right
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

    def __init__(
        self, dialect: "SQLDialectBase", expr: "BaseExpression", value: bool, is_not: bool = False
    ):
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
