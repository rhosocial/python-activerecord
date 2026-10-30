# src/rhosocial/activerecord/backend/expression/query_parts.py
"""
SQL query clause expressions like WHERE, GROUP BY, HAVING, ORDER BY, LIMIT, etc.

These expression classes collect parameters for specific SQL clauses
and delegate SQL generation to backend-specific dialects.
"""

from enum import Enum
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union

from ..expression.objects import Table
from .bases import BaseExpression, SQLPredicate
from .core import Subquery
from .mixins import AliasableMixin
from .objects import Table
from .sources import NamedRelationRef, TableSource


class JoinType(str, Enum):
    """The SQL JOIN types, as the wire word form.

    ``str`` so a member *is* the word it carries and the SQL it writes is a
    per-member property. The join phrase never reaches the artifact: it is a
    spelling, and ``STRAIGHT_JOIN`` alone is enough to show why -- it is MySQL
    dialect spelled inside what is supposed to be a language-neutral payload.

    This is the same shape :class:`~.predicates.ComparisonOperator` and
    :class:`~.operators.ArithmeticOperator` already have.
    """

    #: A member *is* the word it carries; see ``SortDirection.__str__``.
    __str__ = str.__str__

    INNER = "inner"
    JOIN = "join"
    LEFT = "left"
    LEFT_OUTER = "left_outer"
    RIGHT = "right"
    RIGHT_OUTER = "right_outer"
    FULL = "full"
    FULL_OUTER = "full_outer"
    CROSS = "cross"
    #: MySQL-only. A backend-specific spelling belongs to the backend that has
    #: it, but the *operation* is common, so the word is admitted here and the
    #: phrase is left to the formatter.
    STRAIGHT = "straight"

    @property
    def phrase(self) -> str:
        """The SQL this type writes. Never in the artifact."""
        return _JOIN_PHRASES[self]


_JOIN_PHRASES = {
    JoinType.INNER: "INNER JOIN",
    JoinType.JOIN: "JOIN",
    JoinType.LEFT: "LEFT JOIN",
    JoinType.LEFT_OUTER: "LEFT OUTER JOIN",
    JoinType.RIGHT: "RIGHT JOIN",
    JoinType.RIGHT_OUTER: "RIGHT OUTER JOIN",
    JoinType.FULL: "FULL JOIN",
    JoinType.FULL_OUTER: "FULL OUTER JOIN",
    JoinType.CROSS: "CROSS JOIN",
    JoinType.STRAIGHT: "STRAIGHT_JOIN",
}

#: The SQL phrase a caller may still pass, and the member it means. ``join_type``
#: is typed ``str`` at the call site and callers wrote ``"LEFT JOIN"``; accepting
#: the phrase keeps them working while the artifact sees only the word.
_JOIN_PHRASE_TO_TYPE = {phrase: member for member, phrase in _JOIN_PHRASES.items()}


def normalize_join_type(join_type: Any) -> JoinType:
    """Resolve *join_type* to a :class:`JoinType`.

    Accepts a member, a wire word, or the SQL phrase, so ``"LEFT JOIN"`` and
    ``JoinType.LEFT`` build the same node. Anything else raises rather than
    passing through -- a join this node cannot render would otherwise surface
    much later, as malformed SQL.
    """
    if isinstance(join_type, JoinType):
        return join_type
    text = str(join_type).strip()
    upper = text.upper()
    if upper in _JOIN_PHRASE_TO_TYPE:
        return _JOIN_PHRASE_TO_TYPE[upper]
    try:
        return JoinType(text.lower())
    except ValueError:
        raise ValueError(
            f"unknown join type {join_type!r}: the type words are "
            f"{sorted(j.value for j in JoinType)}"
        ) from None


class LockStrength(str, Enum):
    """Row-level lock strength for a locking clause.

    Only the strengths with cross-backend commonality live here. Backends
    with a unique, non-generalisable strength define their own
    ``{Backend}ForUpdateClause`` subclass instead.

    The values are words, not clauses: ``FOR UPDATE`` is a spelling, and the
    artifact has to be readable by an implementation whose dialect writes the
    locking clause differently -- or does not support that strength at all. The
    clause is written by the formatter from :attr:`phrase`.
    """

    #: A member *is* the word it carries; see ``SortDirection.__str__``.
    __str__ = str.__str__

    UPDATE = "update"  # Strongest exclusive lock
    NO_KEY_UPDATE = "no_key_update"  # PostgreSQL-specific weaker exclusive lock
    SHARE = "share"  # Shared lock
    KEY_SHARE = "key_share"  # Weakest shared lock (PostgreSQL)
    LOCK_IN_SHARE_MODE = "lock_in_share_mode"  # Legacy MySQL/MariaDB syntax

    @property
    def phrase(self) -> str:
        """The SQL this strength writes. Never in the artifact."""
        return _LOCK_PHRASES[self]


_LOCK_PHRASES = {
    LockStrength.UPDATE: "FOR UPDATE",
    LockStrength.NO_KEY_UPDATE: "FOR NO KEY UPDATE",
    LockStrength.SHARE: "FOR SHARE",
    LockStrength.KEY_SHARE: "FOR KEY SHARE",
    LockStrength.LOCK_IN_SHARE_MODE: "LOCK IN SHARE MODE",
}

#: The SQL clause a caller may still pass, and the member it means. Accepting it
#: keeps every existing ``strength="FOR UPDATE"`` call site working while the
#: artifact sees only the word.
_LOCK_PHRASE_TO_STRENGTH = {phrase: member for member, phrase in _LOCK_PHRASES.items()}


def normalize_lock_strength(strength: Any) -> LockStrength:
    """Resolve *strength* to a :class:`LockStrength`.

    Accepts a member, a wire word, or the SQL clause, so ``"FOR UPDATE"`` and
    ``LockStrength.UPDATE`` build the same node. Anything else raises rather
    than passing through.
    """
    if isinstance(strength, LockStrength):
        return strength
    text = str(strength).strip()
    upper = text.upper()
    if upper in _LOCK_PHRASE_TO_STRENGTH:
        return _LOCK_PHRASE_TO_STRENGTH[upper]
    try:
        return LockStrength(text.lower())
    except ValueError:
        raise ValueError(
            f"unknown lock strength {strength!r}: the strength words are "
            f"{sorted(s.value for s in LockStrength)}"
        ) from None


if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase
    from .statements import QueryStatement


class WhereClause(BaseExpression):
    """
    Represents a WHERE clause in a SQL query.

    The WHERE clause filters rows based on specified conditions, allowing only
    rows satisfying the predicate to be included in the result set.

    Examples:
        # Basic WHERE clause
        where_clause = WhereClause(
            dialect,
            condition=ComparisonPredicate(dialect, "=", Column(dialect, "status"), Literal(dialect, "active"))
        )

        # Complex WHERE with logical operators
        condition = (
            (Column(dialect, "age") > Literal(dialect, 18))
            & (Column(dialect, "status") == Literal(dialect, "active"))
        )
        where_clause = WhereClause(dialect, condition=condition)
    """

    def __init__(self, dialect: "SQLDialectBase", condition: "SQLPredicate"):
        super().__init__(dialect)
        self.condition = condition  # The filtering condition (predicate)

    def and_(self, predicate: "SQLPredicate") -> "WhereClause":
        """
        Add an AND condition to the existing WHERE clause.

        Args:
            predicate: A SQL predicate to be combined with the existing condition using AND

        Returns:
            Self for method chaining
        """
        # Combine the existing condition with the new predicate using AND
        self.condition = self.condition & predicate
        return self

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_where_clause"


class GroupByHavingClause(BaseExpression):
    """
    Represents combined GROUP BY and HAVING clauses in a SQL query.

    This unified class handles both grouping specifications and group filtering,
    enforcing the dependency that HAVING requires GROUP BY. It centralizes
    validation and SQL generation for these related clauses.

    Examples:
        # Basic GROUP BY only
        group_clause = GroupByHavingClause(
            dialect,
            group_by=[Column(dialect, "category")]
        )

        # GROUP BY with HAVING condition
        group_having_clause = GroupByHavingClause(
            dialect,
            group_by=[Column(dialect, "category")],
            having=FunctionCall(dialect, "COUNT", Column(dialect, "id")) > Literal(dialect, 5)
        )

        # Complex grouping with multiple expressions and filtering
        complex_clause = GroupByHavingClause(
            dialect,
            group_by=[
                FunctionCall(dialect, "YEAR", Column(dialect, "created_at")),
                Column(dialect, "status")
            ],
            having=FunctionCall(dialect, "COUNT", Column(dialect, "id")) > Literal(dialect, 10)
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        group_by: Optional[List["BaseExpression"]] = None,  # List of grouping expressions
        having: Optional["SQLPredicate"] = None,
    ):  # HAVING condition (requires GROUP BY)
        super().__init__(dialect)

        self.group_by = group_by or []
        self.having = having

        # Validate that HAVING requires GROUP BY
        if having is not None and not self.group_by:
            raise ValueError("HAVING clause requires GROUP BY clause")

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_group_by_having_clause"


class OrderByClause(BaseExpression):
    """
    Represents an ORDER BY clause in a SQL query.

    The ORDER BY clause sorts the result set based on specified columns or expressions,
    with optional direction (ASC/DESC) and null order handling.

    Examples:
        # Basic ORDER BY
        order_by = OrderByClause(
            dialect,
            expressions=[(Column(dialect, "name"), "ASC")]
        )

        # Complex ORDER BY with multiple expressions and directions
        order_by = OrderByClause(
            dialect,
            expressions=[
                (Column(dialect, "category"), "ASC"),
                (FunctionCall(dialect, "COUNT", Column(dialect, "id")), "DESC"),
                (Column(dialect, "name"), "ASC")
            ]
        )

        # ORDER BY with expression only (defaults to ASC)
        order_by = OrderByClause(
            dialect,
            expressions=[Column(dialect, "date_created")]
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        expressions: List[
            Union[
                "BaseExpression",  # Expression with default ASC direction
                Tuple["BaseExpression", str],  # (expression, direction)
            ]
        ],
    ):
        super().__init__(dialect)
        # An artifact carries this as an array: JSON draws no distinction between
        # a list and a tuple, and a marker to draw one would be a dispatch every
        # language had to reimplement. The pair is restored here instead, where
        # the parameter's declared type already says what it is -- wide in,
        # normalised out.
        #
        # The direction is normalised here too, not at render time, so what
        # this node holds is already the wire word. Leaving it raw meant a
        # caller who wrote "DESC" shipped "DESC" on the wire while one who wrote
        # "desc" shipped "desc" — the same comparison two spellings for one
        # thing, which is what §11.4 exists to prevent.
        self.expressions = [self._normalize_entry(item) for item in expressions]

    @staticmethod
    def _normalize_entry(item):
        """One ORDER BY element in its single wire form.

        An entry carrying only an operand and a direction is the pair
        ``[node, direction]``; the node form exists for the case the pair cannot
        express, a ``NULLS FIRST`` / ``NULLS LAST`` request. Writing back
        whichever the caller happened to pass would put two spellings for one
        thing on the wire -- and an artifact has to be byte-identical across
        four languages, which it cannot be when it depends on how it was built.
        """
        if not isinstance(item, BaseExpression):
            return (item[0], SortDirection.parse(item[1]))
        # A directionless, null-orderless item means exactly what the pair with
        # no direction means, so it is written as one.
        if isinstance(item, OrderByItem) and item.nulls is None:
            return (item.operand, item.direction)
        return item

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_order_by_clause"


class SortDirection(str, Enum):
    """The two sort directions, as the wire word form.

    Lowercase words, like every other operation on the wire: ``asc`` names the
    direction and ``ASC`` is one spelling of it. The artifact has to be
    byte-identical across four languages, and a SQL keyword is exactly the kind
    of thing they will not agree on — so the keyword is written by the
    formatter, through :attr:`keyword`. ``NullsOrder`` beside this one was
    already written this way; sort direction was the exception.

    ``str`` so a member *is* the word it carries.
    """

    ASC = "asc"
    DESC = "desc"

    #: A member *is* the word it carries: str() and f-string interpolation must
    #: yield the value, not ``ClassName.MEMBER``, or the artifact would carry
    #: the Python spelling. ``(str, Enum)`` alone does not give that --
    #: ``Enum.__str__`` wins -- so it is stated here once.
    __str__ = str.__str__

    @property
    def keyword(self) -> str:
        """The SQL keyword this direction writes. Never in the artifact."""
        return self.value.upper()

    @classmethod
    def parse(cls, word: Optional[str]) -> Optional["SortDirection"]:
        """The member for *word*, or ``None`` when there is no direction.

        Accepts either case, because a caller writing ``"DESC"`` from habit and
        a caller writing the wire word ``"desc"`` mean the same direction.

        ``None`` is accepted because a direction is optional on the wire: this
        module's own :class:`OrderByItem` writes ``null``, so an artifact
        carrying ``[operand, null]`` is one this library produced. Sorting
        without a direction is ordinary rather than malformed, and a reader that
        crashed on it would reject its own output.
        """
        if word is None:
            return None
        if not isinstance(word, str):
            raise ValueError(
                f"Invalid ORDER BY direction: {word!r}. Must be 'asc', 'desc', or null."
            )
        try:
            return cls(word.strip().lower())
        except ValueError:
            raise ValueError(
                f"Invalid ORDER BY direction: {word!r}. Must be 'asc', 'desc', or null."
            ) from None


class NullsOrder(str, Enum):
    """Where nulls sit in an ordering."""

    FIRST = "first"
    LAST = "last"

    #: A member *is* the word it carries: str() and f-string interpolation must
    #: yield the value, not ``ClassName.MEMBER``, or the rendered SQL and the
    #: artifact would carry the Python spelling. ``(str, Enum)`` alone does not
    #: give that -- ``Enum.__str__`` wins -- so it is stated here once.
    __str__ = str.__str__

    @classmethod
    def parse(cls, word: str) -> "NullsOrder":
        """The member for *word*, raising ``ValueError`` if it is not one."""
        try:
            return cls(word.strip().lower())
        except ValueError:
            raise ValueError(
                f"Invalid null ordering: {word!r}. Must be 'first' or 'last'."
            ) from None


class OrderByItem(BaseExpression):
    """A single sort element within an ORDER BY clause.

    This is the *entry*, not the clause: the operand, its direction
    (``ASC`` / ``DESC``) and its null-ordering together make one item, and
    the ``ORDER BY`` clause holding a list of them is :class:`OrderByClause`
    -- a different node with a different formatter. The two are not
    interchangeable: only this one carries the direction and null-order
    triple, and the clause is what a statement renders.

    Per the spec's naming table (§4.9) an ordering entry is the "expression"
    category -- it independently holds something, is not part of a statement
    and does not execute on its own -- which is why ``Item`` and not
    ``Clause`` names it. ``order_by_clause`` stays registered as a read alias
    of ``order_by_item`` for artifacts published by the other three ports.

    ``nulls`` is a single enum-style parameter: ``"first"`` / ``"last"`` spell
    ``NULLS FIRST`` / ``NULLS LAST``, and ``None`` (the default) leaves null
    ordering to the engine. The former ``nulls_first`` / ``nulls_last`` boolean
    pair is gone.

    Examples:
        # Ascending, nulls first
        OrderByItem(dialect, Column(dialect, "name"), nulls="first")

        # Descending
        OrderByItem(dialect, Column(dialect, "created_at"), "DESC")
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        operand: "BaseExpression",
        direction: Optional[SortDirection] = None,
        nulls: Optional[NullsOrder] = None,
    ):
        super().__init__(dialect)
        if direction is not None:
            direction = (
                SortDirection(direction)
                if isinstance(direction, SortDirection)
                else SortDirection.parse(direction)
            )
        if nulls is not None:
            nulls = NullsOrder(nulls) if isinstance(nulls, NullsOrder) else NullsOrder.parse(nulls)
        self.operand = operand
        self.direction = direction
        self.nulls = nulls

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_order_by_item"


class LimitOffsetClause(BaseExpression):
    """
    Represents LIMIT and/or OFFSET clauses in a SQL query.

    The LIMIT clause restricts the number of rows returned, while OFFSET
    skips a specified number of rows before starting to return rows.

    Examples:
        # Basic LIMIT
        limit_clause = LimitOffsetClause(dialect, limit=10)

        # LIMIT with OFFSET
        limit_clause = LimitOffsetClause(dialect, limit=10, offset=20)

        # OFFSET only (some databases support this)
        offset_clause = LimitOffsetClause(dialect, offset=50)
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        limit: Optional[Union[int, "BaseExpression"]] = None,
        offset: Optional[Union[int, "BaseExpression"]] = None,
        with_ties: bool = False,
    ):
        super().__init__(dialect)

        # Validate that offset requires limit in dialects that don't support offset without limit
        if offset is not None and limit is None:
            if not dialect.supports_offset_without_limit():
                raise ValueError(
                    f"OFFSET clause requires LIMIT clause in {dialect.name} dialect. "
                    f"Call .limit() before .offset(), or use .limit(limit, offset=offset)."
                )

        self.limit = limit  # Maximum number of rows to return (optional)
        self.offset = offset  # Number of rows to skip (optional, requires LIMIT in most dialects)
        self.with_ties = with_ties  # FETCH FIRST ... WITH TIES (requires FETCH syntax)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_limit_offset_clause"


class QualifyClause(BaseExpression):
    """
    Represents a QUALIFY clause in a SQL query (available in some SQL dialects like Snowflake).

    The QUALIFY clause filters rows based on the results of window functions,
    similar to how HAVING filters groups based on aggregate function results.

    Examples:
        # QUALIFY with window function results
        window_spec = WindowSpecification(
            dialect,
            partition_by=[Column(dialect, "department")],
            order_by=[(Column(dialect, "salary"), "DESC")]
        )
        rank_func = FunctionCall(dialect, "ROW_NUMBER", window_spec=window_spec)

        qualify_clause = QualifyClause(
            dialect,
            condition=rank_func <= Literal(dialect, 3)  # Top 3 earners per department
        )
    """

    def __init__(self, dialect: "SQLDialectBase", condition: "SQLPredicate"):
        super().__init__(dialect)
        self.condition = condition  # The window function filter condition (predicate)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_qualify_clause"


class ForUpdateClause(BaseExpression):
    """
    Represents a FOR UPDATE clause used for row-level locking in SELECT statements.

    The FOR UPDATE clause locks selected rows preventing other transactions from
    modifying them until the current transaction is committed or rolled back.

    Example Usage:
        # Basic FOR UPDATE
        for_update = ForUpdateClause(dialect)

        # FOR UPDATE with specific columns
        for_update = ForUpdateClause(
            dialect,
            of_columns=[Column(dialect, "id"), "name"]
        )

        # FOR UPDATE with NOWAIT
        for_update = ForUpdateClause(dialect, nowait=True)

        # FOR UPDATE with SKIP LOCKED
        for_update = ForUpdateClause(dialect, skip_locked=True)
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        strength: Optional[Any] = None,
        of_columns: Optional[List[Union[str, "BaseExpression"]]] = None,  # Specify columns to lock
        nowait: bool = False,  # NOWAIT option - fail immediately if locked
        skip_locked: bool = False,  # SKIP LOCKED option - skip locked rows
    ):  # Dialect-specific options
        super().__init__(dialect)
        self.strength = (
            normalize_lock_strength(strength) if strength is not None else LockStrength.UPDATE
        )
        self.of_columns = of_columns or []  # Columns to apply the lock to
        self.nowait = nowait  # If True, fail immediately if rows are locked
        self.skip_locked = skip_locked  # If True, skip locked rows instead of waiting

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_for_update_clause"


class GroupingClause(BaseExpression):
    """Represents grouping operations like ROLLUP, CUBE, and GROUPING SETS."""

    def __init__(
        self, dialect: "SQLDialectBase", operation: str, expressions: List["BaseExpression"]
    ):
        super().__init__(dialect)
        self.operation = operation
        self.expressions = expressions

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_grouping_clause"


class JoinClause(AliasableMixin, TableSource, BaseExpression):
    """
    Represents a JOIN expression (e.g., table1 JOIN table2 ON condition).

    This class collects all parameters for a JOIN operation and delegates
    the SQL generation to the configured dialect for database-specific syntax.

    This class supports chaining of joins using the join() method and convenience methods
    like inner_join(), left_join(), etc., enabling complex multi-table joins.
    As an ``AliasableMixin`` subclass, ``as_()`` returns a NEW aliased copy and
    never mutates the original (see ``AliasableMixin.as_``).

    Example Usage:
        # Basic INNER JOIN with ON condition
        join_expr = JoinClause(
            dialect,
            left_table=NamedRelationRef(dialect, Table(dialect, "users"), alias="u"),
            right_table=NamedRelationRef(dialect, Table(dialect, "orders"), alias="o"),
            join_type=JoinType.INNER,
            condition=Column(dialect, "user_id", "u") == Column(dialect, "user_id", "o")
        )

        # LEFT JOIN with USING clause
        join_expr = JoinClause(
            dialect,
            left_table=NamedRelationRef(dialect, Table(dialect, "employees"), alias="e"),
            right_table=NamedRelationRef(dialect, Table(dialect, "departments"), alias="d"),
            join_type=JoinType.LEFT,
            using=["dept_id"]
        )

        # NATURAL JOIN
        join_expr = JoinClause(
            dialect,
            left_table=NamedRelationRef(dialect, Table(dialect, "table1")),
            right_table=NamedRelationRef(dialect, Table(dialect, "table2")),
            join_type=JoinType.INNER,
            natural=True
        )

        # Chaining joins
        chained_join = join_expr.join(
            right_table=NamedRelationRef(dialect, Table(dialect, "products"), alias="p"),
            join_type="LEFT JOIN",
            condition=Column(dialect, "product_id", "o") == Column(dialect, "id", "p")
        )

        # Using convenience methods
        final_join = chained_join.left_join(
            right_table=NamedRelationRef(dialect, Table(dialect, "categories"), alias="c"),
            condition=Column(dialect, "category_id", "p") == Column(dialect, "id", "c")
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        left_table: Union[str, "NamedRelationRef", "Subquery", "QueryStatement", "JoinClause"],
        right_table: Union[str, "NamedRelationRef", "Subquery", "QueryStatement", "JoinClause"],
        join_type: str = "JOIN",
        condition: Optional[
            "SQLPredicate"
        ] = None,  # ON condition (mutually exclusive with 'using')
        using: Optional[
            List[str]
        ] = None,  # USING clause columns (mutually exclusive with 'condition')
        natural: bool = False,  # NATURAL join flag
        alias: Optional[str] = None,  # Alias for the joined result
    ):  # Dialect-specific options
        super().__init__(dialect)

        from .graph import GraphTableExpression
        from .statements import QueryStatement

        # Normalize table inputs. A join reads from both sides, so each side is a
        # row source; a bare name becomes a source over a plain table object.
        self.left_table = (
            left_table
            if isinstance(
                left_table,
                (
                    Table,
                    NamedRelationRef,
                    Subquery,
                    JoinClause,
                    QueryStatement,
                    GraphTableExpression,
                ),
            )
            else NamedRelationRef(dialect, Table(dialect, str(left_table)))
        )
        self.right_table = (
            right_table
            if isinstance(
                right_table,
                (
                    Table,
                    NamedRelationRef,
                    Subquery,
                    JoinClause,
                    QueryStatement,
                    GraphTableExpression,
                ),
            )
            else NamedRelationRef(dialect, Table(dialect, str(right_table)))
        )

        # Resolved to a JoinType so the artifact carries the word. A caller may
        # still pass the SQL phrase -- see normalize_join_type.
        self.join_type = normalize_join_type(join_type)

        # Validate mutual exclusivity of condition and using
        if condition is not None and using is not None:
            raise ValueError(
                "Cannot specify both 'condition' (ON) and 'using' (USING) clauses in a JOIN"
            )

        # Store other parameters
        self.condition = condition  # ON condition
        self.using = using  # USING columns
        self.natural = natural  # NATURAL join flag
        self.alias = alias  # Alias for the join result

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_join_clause"

    def join(
        self,
        right_table: Union[str, "NamedRelationRef", "Subquery", "QueryStatement", "JoinClause"],
        join_type: str = "JOIN",
        condition: Optional["SQLPredicate"] = None,
        using: Optional[List[str]] = None,
        natural: bool = False,
        alias: Optional[str] = None,
    ) -> "JoinClause":
        """
        Create a new JoinClause by joining the current expression to another table.

        This enables chaining of joins like:
        join1.join(table2, "INNER JOIN", condition=...).join(table3, "LEFT JOIN", condition=...)

        Args:
            right_table: The table to join with
            join_type: Type of join (e.g., "INNER JOIN", "LEFT JOIN", etc.)
            condition: Join condition (ON clause)
            using: Using columns (USING clause)
            natural: Whether to use NATURAL join
            alias: Alias for the resulting join

        Returns:
            A new JoinClause representing the chained join
        """
        # Create a new JoinClause with this instance as the left table
        return JoinClause(
            dialect=self.dialect,
            left_table=self,  # Use current join expression as left table
            right_table=right_table,
            join_type=join_type,
            condition=condition,
            using=using,
            natural=natural,
            alias=alias,
        )

    def inner_join(
        self,
        right_table: Union[str, "NamedRelationRef", "Subquery", "QueryStatement", "JoinClause"],
        condition: Optional["SQLPredicate"] = None,
        using: Optional[List[str]] = None,
        alias: Optional[str] = None,
    ) -> "JoinClause":
        """Create an inner join with another table."""
        return self.join(
            right_table=right_table,
            join_type="INNER JOIN",
            condition=condition,
            using=using,
            alias=alias,
        )

    def left_join(
        self,
        right_table: Union[str, "NamedRelationRef", "Subquery", "QueryStatement", "JoinClause"],
        condition: Optional["SQLPredicate"] = None,
        using: Optional[List[str]] = None,
        alias: Optional[str] = None,
    ) -> "JoinClause":
        """Create a left join with another table."""
        return self.join(
            right_table=right_table,
            join_type="LEFT JOIN",
            condition=condition,
            using=using,
            alias=alias,
        )

    def right_join(
        self,
        right_table: Union[str, "NamedRelationRef", "Subquery", "QueryStatement", "JoinClause"],
        condition: Optional["SQLPredicate"] = None,
        using: Optional[List[str]] = None,
        alias: Optional[str] = None,
    ) -> "JoinClause":
        """Create a right join with another table."""
        return self.join(
            right_table=right_table,
            join_type="RIGHT JOIN",
            condition=condition,
            using=using,
            alias=alias,
        )

    def full_join(
        self,
        right_table: Union[str, "NamedRelationRef", "Subquery", "QueryStatement", "JoinClause"],
        condition: Optional["SQLPredicate"] = None,
        using: Optional[List[str]] = None,
        alias: Optional[str] = None,
    ) -> "JoinClause":
        """Create a full join with another table."""
        return self.join(
            right_table=right_table,
            join_type="FULL JOIN",
            condition=condition,
            using=using,
            alias=alias,
        )

    def cross_join(
        self,
        right_table: Union[str, "NamedRelationRef", "Subquery", "QueryStatement", "JoinClause"],
        alias: Optional[str] = None,
    ) -> "JoinClause":
        """Create a cross join with another table."""
        return self.join(right_table=right_table, join_type="CROSS JOIN", alias=alias)
