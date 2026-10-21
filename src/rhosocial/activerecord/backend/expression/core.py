# src/rhosocial/activerecord/backend/expression/core.py
"""
Core SQL expression components like columns, literals, function calls, and subqueries.
"""

from typing import Any, Optional, Tuple, TYPE_CHECKING, Union

from .bases import BaseExpression, QueryWithParams, SQLPredicate, SQLQueryAndParams, SQLValue
from .column_types import ColumnBase
from .mixins import (
    AliasableMixin,
    ArithmeticMixin,
    BooleanLogicMixin,
    ComparisonMixin,
    NotANumberMixin,
    ResultTypeMixin,
    StringPatternPredicateMixin,
    TypeCastingMixin,
)

if TYPE_CHECKING:
    from .sources import NamedRelationRef  # pragma: no cover
    from ..dialect import SQLDialectBase
    from .advanced_functions import WindowSpecification
    from .types._base import DataType


class Literal(BaseExpression):
    """A literal, and nothing but the decision of how it reaches SQL.

    Every value that reaches SQL passes through this class, so that the question
    "does this value become a bind parameter or SQL text?" has exactly one place
    that answers it. Nothing else in the tree has to know: a formatter calls
    ``child.to_sql()`` and gets ``(sql, params)`` back, whether the child was a
    function call or a value.

    :attr:`inline` is that answer, and it is per **position** rather than per
    class. A node whose values all take the same treatment never needs it — the
    default, ``False``, binds, which is what every DQL/DML data position wants.
    A DDL syntax position that accepts no bind parameters at all passes
    ``inline=True`` and gets escaped SQL text instead. Where one node holds
    several values and only some of them are exempt from binding, this is the
    only way to say so.

    What the class deliberately does **not** claim is what kind of value this
    is. It is not a :class:`~...bases.SQLValue`: that category says "this
    expression yields a value of some type", and a bare position does not know
    its type — ``NULLIF(a, b)`` is text or a number depending on the data. The
    earlier version of this class inherited the comparison, arithmetic and
    string-pattern mixins, which let ``Literal(d, 7).like()`` compile and
    promised SQL the database would reject. The result's type is declared
    elsewhere, by :meth:`~...mixins.ResultTypeMixin.as_text` and its siblings.

    Nor is a literal aliasable. A bind parameter has no name to give — the
    parameter the driver fills in is the driver's, not the query's — and a name
    on SQL text would be naming text rather than a result. Aliasing belongs to
    the things that produce a named result, which is what
    :class:`~...bases.SQLValue` is for.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_literal_expression"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        value: Any,
        *,
        inline: bool = False,
    ):
        super().__init__(dialect)
        from .values import LiteralKind

        # Which value kind this is, read off the host value. It is the artifact
        # identity, and it cannot be derived from the class: one class carries
        # every value, while the wire still names the twelve kinds separately --
        # ``"2020-01-02"`` as a date and as a string are the same bytes, and
        # only the kind tells them apart.
        #
        # ``None`` for a type no kind names -- a ``Point``, an ``inet``, any
        # ``SQLLiteral`` implementor. The literal still renders through the
        # dialect's own literal construction; what it cannot do is travel, and
        # serialization is where that is said.
        self.value_kind = LiteralKind.match(value)
        self.value = value
        self.inline = inline

    def __repr__(self) -> str:
        where = "" if not self.inline else ", inline"
        return f"Literal({self.value!r}{where})"


class Column(ColumnBase):
    """A column reference whose type is not known: it renders, and that is all.

    This is the **bare** column. Nothing established what it holds, so it
    offers no operation at all — not comparison, not ``LIKE``, not arithmetic.
    The previous shape (the whole operation set, on the theory that offering
    less would be guessing) had the failure the typed classes exist to
    prevent: a caller compared two of them and got Python's *identity*
    answer, silently, instead of SQL. A bare reference that cannot say what
    it holds cannot promise an operation the database will accept either, so
    it promises nothing and the query layer builds its predicates
    explicitly — :class:`~...expression.predicates.ComparisonPredicate`,
    ``InPredicate``, ``IsNullPredicate`` — which work on any column because
    they ask the *dialect*, not the column, for the SQL.

    Two things lead here:

    * **A string at a public entry point.** ``order_by("name")``,
      ``count("price")`` and ``select("id")`` accept a column name as text.
      The framework has no annotation to consult, so it cannot know what the
      column holds. Pass the model proxy instead, ``order_by(User.c.name)``,
      and the column arrives typed.
    * **A model field whose annotation cannot be classified** (``Any``, an
      unresolvable ``Union``) — the field's operations are unknown, and a
      class that guessed them would be the bug the narrow classes prevent.

    An explicit ``UseColumnType(Column)`` declaration reaches this class too;
    what it says is "render the reference and build predicates elsewhere".
    When the type *is* known,
    :class:`FieldProxy<rhosocial.activerecord.base.field_proxy.FieldProxy>`
    returns the narrow class instead, so ``User.c.age`` is an
    :class:`~...expression.column_types.IntegerColumn` and offers no
    ``.like()``. The class identity of a typed column does not vary by
    backend; only its storage does.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_column"


class LogicalValue(
    AliasableMixin,
    ComparisonMixin,
    BooleanLogicMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
):
    """A boolean value expression used in SELECT lists.

    Renders TRUE/FALSE or boolean logic (AND/OR/NOT) as a **value** that can
    appear in a SELECT column list. Not a predicate — does not belong in
    WHERE/HAVING clauses.

    A predicate and this expression render the same SQL; what differs is what
    the caller may do with the result. Combining predicates stays a predicate
    -- that is how ``WHERE`` clauses are built -- while a truth value keeps
    its value type: ``(a & b)`` can be aliased into a ``SELECT`` list,
    compared, cast, and combined further. The class carries the same ``op``
    and ``operands`` shape
    :class:`~...predicates.LogicalPredicate` does, so both go through the one
    dialect entry point (``format_logical_predicate``).
    """

    def __init__(self, dialect: Any, op: str, *operands: Any):
        super().__init__(dialect)
        self.op = op
        # The names are the renderer's: the dialect formatter reads ``op`` and
        # ``operands`` whatever class carried them in, and the expression
        # contract stores every ``__init__`` parameter under its own name.
        self.operands = list(operands)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_logical_predicate"
class FunctionCall(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringPatternPredicateMixin,
    TypeCastingMixin,
    ResultTypeMixin,
    SQLValue,
):
    """Represents a SQL function call, scalar or aggregate, such as LOWER, CONCAT, COUNT, SUM.

    One node covers both because the grammar is one grammar: ``NAME(args)``
    gains ``DISTINCT``, a ``FILTER (WHERE ...)`` clause, an ``OVER (...)``
    window clause and an alias, in that order. What distinguishes an aggregate
    is a fact about the call, not a shape of the SQL, and it is stated at
    construction time by the aggregate factories (``is_aggregate=True``)
    rather than inferred from the name. That fact is read only by RETURNING
    validation, which must refuse an aggregate because a RETURNING clause is
    evaluated per row; it is not a type and says nothing about what the call
    yields.

    The typed result is said by the wrapper the factories return, not by this
    node.

    Carries :class:`ResultTypeMixin` because this is the node that does *not*
    know what it yields. Most functions state their own result by returning the
    matching value class; the ones that cannot -- ``NULLIF`` and the
    ``COALESCE``-shaped family -- come back as this, and the caller says what
    they produce with ``.as_text()`` and friends.

    When niladic=True and no arguments are provided, the function call
    generates SQL without parentheses (e.g., CURRENT_TIMESTAMP instead of
    CURRENT_TIMESTAMP()). Per SQL:2003, certain value functions are niladic
    and must not use parentheses when invoked without arguments.

    When a niladic function has arguments (e.g., CURRENT_TIMESTAMP(6)),
    parentheses are included as normal.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_function_call"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        func_name: str,
        *args: "BaseExpression",
        is_distinct: bool = False,
        alias: Optional[str] = None,
        niladic: bool = False,
        filter_predicate: Optional["SQLPredicate"] = None,
        window_spec: Optional[Union["WindowSpecification", str]] = None,
        is_aggregate: bool = False,
    ):
        super().__init__(dialect)
        self.func_name = func_name
        self.args = list(args)
        self.is_distinct = is_distinct
        self.alias = alias
        self.niladic = niladic
        self.filter_predicate = filter_predicate
        self.window_spec = window_spec
        self.is_aggregate = is_aggregate

    def filter(self, predicate: "SQLPredicate") -> "FunctionCall":
        """Apply a ``FILTER (WHERE ...)`` clause to this call.

        A second call AND-combines with the filter already attached, so
        ``call.filter(a).filter(b)`` states both conditions. Returns this
        node, which is what the fluent chain continues on; note that a typed
        wrapper around this node forwards the call and hands the node back,
        so the result is untyped -- filtering does not re-type anything.
        """
        if self.filter_predicate:
            self.filter_predicate = self.filter_predicate & predicate
        else:
            self.filter_predicate = predicate
        return self

    def over(self, window_spec: Union["WindowSpecification", str]) -> "FunctionCall":
        """Attach an ``OVER (...)`` clause to this call.

        The working replacement for assigning ``window_spec`` on the object:
        a typed wrapper stores an assignment on itself while rendering reads
        the node it holds, so the assignment is a silent no-op there. This
        method lives on the node, where the renderer looks. Returns this
        node, so the fluent chain continues on it.

        *window_spec* is an inline :class:`WindowSpecification` or the name
        of a window defined elsewhere in the query, which renders as an
        identifier.
        """
        self.window_spec = window_spec
        return self


class CastExpression(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringPatternPredicateMixin,
    TypeCastingMixin,
    SQLValue,
):
    """Represents a SQL type cast as a proper AST node.

    The ``Expression`` suffix is not a fallback spelling: it transcribes the
    standard production this node stands for -- ISO/IEC 9075-2
    ``<cast specification>``. Per spec §4.9 (the "scalar expression special
    forms" row) a CAST is a scalar-expression production rather than a routine
    invocation, so it is neither a ``*Function`` nor a ``*Clause``; the name is
    kept verbatim from the standard and the ``*Expression`` suffix is the
    retired spelling's single exemption class.

    ``CAST(expression AS target_type)`` is a **unary tree node**: its single
    child is the wrapped expression and ``target_type`` is a construction
    parameter. Rendering is delegated to the dialect's
    ``format_cast_expression``.

    Chained ``cast()`` calls therefore nest like any other expression —
    ``expr.cast(A).cast(B)`` renders ``CAST(CAST(expr AS A) AS B)``.
    When the wrapped expression carries an alias, ``cast()`` hoists the
    alias onto the new node (the alias decorates the outermost rendered
    form), so ``col.cast(IntegerType(dialect)).as_("v")`` and
    ``col.as_("v").cast(IntegerType(dialect))`` both render
    ``CAST(col AS INTEGER) AS v``.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_cast_expression"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        expression: "SQLValue",
        target_type: "DataType",
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        from .types._base import DataType as _DataType

        if not isinstance(target_type, _DataType):
            # The type position of CAST(expr AS type) is a grammar production,
            # not an expression, so no bound parameter can be used there and a
            # free-form string would be rendered straight into the statement.
            # Requiring a DataType makes that impossible by construction rather
            # than by validating a string that someone else can widen later.
            raise TypeError(
                f"cast() takes a DataType instance, not "
                f"{type(target_type).__name__}. Use IntegerType(dialect) rather "
                f"than a string: the type position cannot be bound, so a string "
                f"is rendered into the SQL. A user-defined type is a DataType "
                f"subclass, registered so dialects can render it."
            )
        self.expression = expression
        self.target_type = target_type
        self.alias = alias

    def __repr__(self) -> str:
        return f"CastExpression({self.expression!r} AS {self.target_type!r})"


class Subquery(AliasableMixin, ArithmeticMixin, ComparisonMixin, TypeCastingMixin, SQLValue):
    """Represents a subquery in a SQL expression."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_subquery"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        query_input: Union[str, "SQLQueryAndParams", "BaseExpression", "Subquery"],
        query_params: Optional[Tuple[Any, ...]] = None,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.alias = alias

        # Handle backward compatibility: if query_input is not a tuple but query_params is provided,
        # treat query_input as a string and query_params as the parameters
        if query_params is not None and not isinstance(query_input, tuple):
            # Old-style call: Subquery(dialect, query_string, query_params, alias)
            self.query_input = query_input
            self.query_params = query_params or ()
        else:
            # New-style call or other cases
            query = query_input
            if isinstance(query, str):
                # If input is a string, use it directly with empty params
                self.query_input = query
                self.query_params = ()
            elif QueryWithParams.holds(query):
                # If input is a SQLQueryAndParams (str, tuple), extract SQL and params
                sql_str, params = query
                # If params is None, use an empty tuple
                self.query_params = params if params is not None else ()
                self.query_input = sql_str
            elif isinstance(query, Subquery):
                # If input is already a Subquery, copy its attributes
                self.query_input = query.query_input
                self.query_params = query.query_params
                self.alias = query.alias or alias
            elif isinstance(query, BaseExpression):
                # If input is a BaseExpression, call its to_sql method
                self.query_input, self.query_params = query.to_sql()
            else:
                # Default: treat as string
                self.query_input = str(query)
                self.query_params = ()


class QualifiedIdentifier(BaseExpression):
    """Represents a schema-qualified identifier (e.g., schema.table_name).

    Per-role quoting fields (all default to ``True``):
    - ``name_need_quote`` ↔ ``name``
    - ``schema_need_quote`` ↔ ``schema``
    """

    @property
    def format_method(self) -> str:
        return "format_qualified_identifier"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        schema: Optional[str] = None,
        name: str = "",
        name_need_quote: bool = True,
        schema_need_quote: bool = True,
    ):
        super().__init__(dialect)
        self.name_need_quote = self.quote_flag(name_need_quote, "name_need_quote")
        self.schema_need_quote = self.quote_flag(schema_need_quote, "schema_need_quote")
        self.schema = schema
        self.name = name


class AllColumnsWildcard(SQLValue):
    """Every column of a relation source: the select-list ``*``.

    Its standing is that of a column reference, and its home is the select
    list and the RETURNING clause -- the spec's first wildcard class (4.10.1).
    A bare ``*`` (``relation`` empty) lets the surrounding clause decide what
    "all columns" spans: every FROM source in a select list, the DML target
    in RETURNING. The clause's formatter injects that scope; this node does
    not know where it sits and must not probe.

    A ``relation`` present renders the qualified ``rel.*`` -- the reference
    spelling the query itself uses (the alias when aliased, the qualified
    name otherwise). Row counting is a different contract: the asterisk in
    ``COUNT(*)`` counts rows rather than expanding columns, and belongs to
    :class:`RowCountWildcard` alone.
    """

    @property
    def format_method(self) -> str:
        return "format_all_columns_wildcard"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        relation: Optional["NamedRelationRef"] = None,
    ):
        super().__init__(dialect)
        self.relation = relation


class RowCountWildcard(SQLValue):
    """The asterisk that counts rows: ``COUNT(*)``'s parameter.

    The spec's second wildcard class (4.10.2). Its semantics are rows, not
    column expansion, so it accepts no relation: standard ``COUNT(*)`` takes
    the bare asterisk, and the qualified ``COUNT(t.*)`` is a different
    (non-NULL row count) that supporting backends define as their own derived
    node. The only aggregate whose contract admits this node is ``COUNT``;
    ``SUM``/``AVG``/``MAX``/``MIN`` refuse it where they are built.
    """

    @property
    def format_method(self) -> str:
        return "format_row_count_wildcard"

    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)