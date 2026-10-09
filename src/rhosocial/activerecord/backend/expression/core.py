# src/rhosocial/activerecord/backend/expression/core.py
"""
Core SQL expression components like columns, literals, function calls, and subqueries.
"""

import copy
from typing import Any, Optional, Tuple, TYPE_CHECKING, Union

from .bases import BaseExpression, SQLPredicate, SQLQueryAndParams, SQLValueExpression, is_sql_query_and_params
from .column_types import ColumnBase
from .mixins import (
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    ArrayMixin,
    DateTimeMixin,
    StringToIntegerMixin,
    JSONAccessorMixin,
    LogicalMixin,
    NotANumberMixin,
    NotComparableMixin,
    NullTestMixin,
    NumericValueMixin,
    ResultTypeMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TranscendentalMixin,
    TypeCastingMixin,
    WrappedCallMixin,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase
    from .advanced_functions import WindowSpecification
    from .types._base import DataType


class Literal(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringPatternPredicateMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """Represents a literal value in a SQL query.

    ``inline_literals`` (a construction-time, factory choice made through the
    ``ToSQLProtocol`` contract) decides how this literal renders: when
    ``True`` the value is spliced into the SQL text via
    ``dialect.format_literal`` (no bind parameter); when ``False`` (the safe
    default) it renders as a bind parameter. Rendering is a pure read of
    this already-collected state.
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
        alias: Optional[str] = None,
        inline_literals: bool = False,
    ):
        super().__init__(dialect)
        self.value = value
        self.alias = alias
        self.inline_literals = inline_literals

    def __repr__(self) -> str:
        return f"Literal({self.value!r}, inline_literals={self.inline_literals!r})"


class Column(
    ComparisonMixin,
    ArithmeticMixin,
    StringPatternPredicateMixin,
    JSONAccessorMixin,
    ColumnBase,
):
    """A column reference whose type is not known.

    This is the **untyped** column: nothing established what it holds, so it
    carries the whole operation set. Offering less would mean guessing, and a
    guess that removes an operation the caller needed is worse than one that
    offers an operation the database will reject.

    Two things lead here:

    * **A string at a public entry point.** ``order_by("name")``,
      ``count("price")`` and ``select("id")`` accept a column name as text.
      The framework has no annotation to consult, so it cannot know what the
      column holds -- and a string here is not safe, because nothing checked
      the name. Pass the model proxy instead, ``order_by(User.c.name)``, and
      the column arrives typed.
    * **A model field whose annotation cannot be classified** (``Any``, an
      unresolvable ``Union``) must not lose operations it may well support.

    When the type *is* known,
    :class:`FieldProxy<rhosocial.activerecord.base.field_proxy.FieldProxy>`
    returns the narrow class instead, so ``User.c.age`` is an
    :class:`~...expression.column_types.IntegerColumn` and offers no
    ``.like()``. The class identity of a typed column does not vary by backend;
    only its storage does.

    The one thing a typed column cannot do is render itself, because
    :class:`~...expression.column_types.ColumnBase` deliberately declares no
    formatting method -- a column with no type has nothing to say about how it
    spells itself. This class supplies that spelling, which is why it is the
    only concrete column class rather than an abstract one.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        table: Optional[str] = None,
        alias: Optional[str] = None,
        schema_name: Optional[str] = None,
        name_need_quote: bool = True,
        alias_need_quote: bool = True,
        schema_need_quote: bool = True,
        table_need_quote: bool = True,
    ):
        super().__init__(
            dialect,
            name,
            table=table,
            alias=alias,
            schema_name=schema_name,
            name_need_quote=name_need_quote,
            alias_need_quote=alias_need_quote,
            schema_need_quote=schema_need_quote,
            table_need_quote=table_need_quote,
        )


class TemporalValueExpression(
    WrappedCallMixin,
    AliasableMixin,
    ComparisonMixin,
    DateTimeMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValueExpression,
):
    """Shared base for the four temporal value types.

    A date, a time, a timestamp and an interval offer the same operations --
    ``date_add``, ``date_sub``, ``date_diff``, ``date_part``, ``extract`` -- and
    none of them supports ``upper``, so the operations live here and the
    subclasses say only which kind of temporal value they are.

    They are four classes rather than one because they are four types. A
    timestamp added to an interval is a timestamp; a date added to an interval
    is not legal in most backends, and nothing about a span says it can be
    extracted from. With one class and a label those differences would have had
    to be spelled as data, and the operations a caller could reach would be the
    union of four unrelated ones.

    Subclasses exist so that ``current_date()`` and ``current_timestamp()``
    arrive already typed. Neither carries ``StringPatternPredicateMixin``:
    a temporal value is not text.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        call: "FunctionCall",
    ):
        super().__init__(dialect)
        self.call = call

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_function_call"

    def to_sql(self):
        """Render the wrapped function call.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        alias = self.__dict__.get("alias")
        if alias and getattr(self.call, "alias", None) != alias:
            call = copy.copy(self.call)
            call.alias = alias
            return call.to_sql()
        return self.call.to_sql()


class DateValueExpression(TemporalValueExpression):
    """A date with no time component. ``CURRENT_DATE`` answers with one."""


class TimeValueExpression(TemporalValueExpression):
    """A time of day. ``CURRENT_TIME`` answers with one."""


class TimestampValueExpression(TemporalValueExpression):
    """A date and a time together. ``NOW()`` and ``CURRENT_TIMESTAMP`` answer
    with one, and adding an interval to it gives another."""


class IntervalValueExpression(TemporalValueExpression):
    """A span of time rather than a point in it.

    An interval is not a timestamp and does not add to one, which is why it is
    its own type here and not a ``date_add`` argument that happens to be
    special. The arithmetic a span supports is what
    :class:`~...expression.mixins.ArithmeticMixin` gives every numeric-like
    value; this class carries the temporal operations that do not apply.
    """


class JSONValueExpression(
    WrappedCallMixin,
    AliasableMixin,
    ComparisonMixin,
    JSONAccessorMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """A JSON document that is not a column reference.

    The result of json_build_object, json_array_elements and the aggregate that
    assembles documents. Carries the JSON accessors, so a built document can
    be walked the same way a column can — json_path is scalar and terminal,
    json_value keeps a document to chain on."""


    def __init__(
        self,
        dialect: "SQLDialectBase",
        call: "FunctionCall",
   ):
        super().__init__(dialect)
        self.call = call

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_function_call"

    def to_sql(self):
        """Render the wrapped function call.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        alias = self.__dict__.get("alias")
        if alias and getattr(self.call, "alias", None) != alias:
            call = copy.copy(self.call)
            call.alias = alias
            return call.to_sql()
        return self.call.to_sql()


class ArrayValueExpression(
    WrappedCallMixin,
    AliasableMixin,
    ComparisonMixin,
    ArrayMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValueExpression,
):
    """A sequence that is not a column reference.

    The result of unnest and of the aggregate that collects into one. Carries
    the array operations, so a collected sequence can be measured or expanded
    the same way a column can."""


    def __init__(
        self,
        dialect: "SQLDialectBase",
        call: "FunctionCall",
   ):
        super().__init__(dialect)
        self.call = call

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_function_call"

    def to_sql(self):
        """Render the wrapped function call.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        alias = self.__dict__.get("alias")
        if alias and getattr(self.call, "alias", None) != alias:
            call = copy.copy(self.call)
            call.alias = alias
            return call.to_sql()
        return self.call.to_sql()


class BooleanValueExpression(
    WrappedCallMixin,
    AliasableMixin,
    ComparisonMixin,
LogicalMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValueExpression,
):
    """A true/false value that is not a column reference.

    A boolean is a value, not a predicate, so it can be aliased, projected and
    compared. It does not extend: every operation on it yields a predicate or
    a boolean, so there is nothing further to chain."""


    def __init__(
        self,
        dialect: "SQLDialectBase",
        call: "FunctionCall",
   ):
        super().__init__(dialect)
        self.call = call

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_function_call"

    def to_sql(self):
        """Render the wrapped function call.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        alias = self.__dict__.get("alias")
        if alias and getattr(self.call, "alias", None) != alias:
            call = copy.copy(self.call)
            call.alias = alias
            return call.to_sql()
        return self.call.to_sql()


class BinaryValueExpression(
    WrappedCallMixin,
    AliasableMixin,
    ComparisonMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValueExpression,
):
    """Raw bytes that are not a column reference.

    There is no byte operation to offer, so this carries comparisons and
    casting. It exists so a function that returns bytes says so instead of being
    unknown."""


    def __init__(
        self,
        dialect: "SQLDialectBase",
        call: "FunctionCall",
   ):
        super().__init__(dialect)
        self.call = call

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_function_call"

    def to_sql(self):
        """Render the wrapped function call.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        alias = self.__dict__.get("alias")
        if alias and getattr(self.call, "alias", None) != alias:
            call = copy.copy(self.call)
            call.alias = alias
            return call.to_sql()
        return self.call.to_sql()


class XMLValueExpression(
    WrappedCallMixin,
    AliasableMixin,
    NotComparableMixin,
    NullTestMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValueExpression,
):
    """An XML document that is not a column reference.

    Returned by the SQL/XML constructors, by the XML access operations, and by
    a cast to :class:`~...types.XmlType`. Same wrapper shape as
    :class:`BinaryValueExpression` -- it holds the call it was built from and
    forwards its alias -- with one difference: an XML value cannot be compared.

    That is the whole surface of XML on the backends that have it. PostgreSQL
    refuses ``xml = xml`` ("operator does not exist: xml = xml") along with
    ordering and ``IN``; SQL Server documents that "the xml data type cannot
    be compared or sorted"; Oracle's ``XMLType`` has no comparison operators
    either. What they all accept is ``IS NULL``, which is why the null tests
    :class:`NullTestMixin` provides stay while :class:`NotComparableMixin`
    refuses the rest. Casting stays too: the way to ask a question of an XML
    value is to cast it or to use a SQL/XML function, not to compare it.
    """


    def __init__(
        self,
        dialect: "SQLDialectBase",
        call: "FunctionCall",
   ):
        super().__init__(dialect)
        self.call = call

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_function_call"

    def to_sql(self):
        """Render the wrapped function call.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        alias = self.__dict__.get("alias")
        if alias and getattr(self.call, "alias", None) != alias:
            call = copy.copy(self.call)
            call.alias = alias
            return call.to_sql()
        return self.call.to_sql()


class UUIDValueExpression(
    WrappedCallMixin,
    AliasableMixin,
    ComparisonMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValueExpression,
):
    """A UUID that is not a column reference.

    Same shape as the binary wrapper: comparisons and casting, and nothing to
    extend with. A backend that cannot generate one raises at the factory rather
    than returning an untyped node."""


    def __init__(
        self,
        dialect: "SQLDialectBase",
        call: "FunctionCall",
   ):
        super().__init__(dialect)
        self.call = call

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_function_call"

    def to_sql(self):
        """Render the wrapped function call.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        alias = self.__dict__.get("alias")
        if alias and getattr(self.call, "alias", None) != alias:
            call = copy.copy(self.call)
            call.alias = alias
            return call.to_sql()
        return self.call.to_sql()


class NumericValueExpression(
    WrappedCallMixin,
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    NumericValueMixin,
    TranscendentalMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """A fractional-valued expression that is not a column reference.

    The result of ``sqrt``, ``log``, ``abs`` on a fractional operand, ``avg``,
    ``percent_rank`` and the other math functions. Carries arithmetic, so
    numeric expressions compose, and comparisons, which every value can do.
    Not the pattern predicates: ``LIKE`` is text matching, and a fraction is not
    text, so ``sqrt(x).like('1%')`` fails here rather than at the database.

    ``ceil``, ``floor`` and ``truncate`` do *not* land here when the operand is
    integral — a whole number rounded to a whole number is an integer, and
    saying otherwise would offer ``bit_length`` on the result of ``ceil``.
    """


    def __init__(self, dialect: "SQLDialectBase", call: "FunctionCall"):
        super().__init__(dialect)
        self.call = call

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_function_call"

    def to_sql(self):
        """Render the wrapped function call.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        # as_() sets the alias on this wrapper, but the rendering happens in
        # the wrapped call, which has its own alias and knows nothing about
        # this one. Handing the alias down is what keeps `length().as_("n")`
        # from silently rendering as a bare LENGTH(x).
        alias = self.__dict__.get("alias")
        if alias and getattr(self.call, "alias", None) != alias:
            call = copy.copy(self.call)
            call.alias = alias
            return call.to_sql()
        return self.call.to_sql()

class IntegerValueExpression(
    WrappedCallMixin,
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    NumericValueMixin,
    TranscendentalMixin,
    TypeCastingMixin,
    SQLValueExpression,
):

    """An integer-valued expression that is not a column reference.

    Returned by the string operations whose result is a number — ``length``,
    ``ascii``, ``strpos``, ``position``, ``octet_length``, ``bit_length`` — so
    that ``col.length() > 5`` reads naturally and ``col.length().upper()``
    fails, which it should: there is no such thing as an upper-cased length.

    It carries :class:`ArithmeticMixin`, so integer arithmetic is available
    and stays an integer. It carries comparisons, which every value can do, and
    not the pattern predicates: ``LIKE`` is text matching, and a whole number is
    not text. That absence is the point of the class — ``length().like("1%")``
    has to fail at the call, naming the operation, rather than be accepted here
    and rejected by the server minutes later.
    """

    def __init__(self, dialect: "SQLDialectBase", call: "FunctionCall"):
        super().__init__(dialect)
        self.call = call

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_function_call"

    def to_sql(self):
        """Render the wrapped function call.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        # as_() sets the alias on this wrapper, but the rendering happens in
        # the wrapped call, which has its own alias and knows nothing about
        # this one. Handing the alias down is what keeps `length().as_("n")`
        # from silently rendering as a bare LENGTH(x).
        alias = self.__dict__.get("alias")
        if alias and getattr(self.call, "alias", None) != alias:
            call = copy.copy(self.call)
            call.alias = alias
            return call.to_sql()
        return self.call.to_sql()

class StringValueExpression(
    WrappedCallMixin,
    AliasableMixin,
    ComparisonMixin,
    StringToIntegerMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValueExpression,
):

    """A string-valued expression that is not a column reference.

    This is what makes the string value operations chain. ``col.upper()``
    returns one of these rather than a bare ``FunctionCall``, so the next
    operation in the chain is available: ``col.upper().substr(0, 3)`` is
    ``SUBSTRING(UPPER("name"), 1, 3)`` and the result is still a string.

    It is deliberately **not** a :class:`StringColumn`. A column names a field
    and ``format_column`` reads ``name`` / ``table`` / ``schema_name``; a
    derived value has none of those, so claiming to be a column would be a lie
    about the object. What it shares with a string column is the *value type*,
    which is what decides which operations are offered.

    The class mirrors :class:`~...expression.advanced_functions.JSONDocumentExpression`,
    which plays the same role for the JSON family.
    """

    def __init__(self, dialect: "SQLDialectBase", call: "FunctionCall"):
        super().__init__(dialect)
        self.call = call

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_function_call"

    def to_sql(self):
        """Render the wrapped function call.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        # as_() sets the alias on this wrapper, but the rendering happens in
        # the wrapped call, which has its own alias and knows nothing about
        # this one. Handing the alias down is what keeps `length().as_("n")`
        # from silently rendering as a bare LENGTH(x).
        alias = self.__dict__.get("alias")
        if alias and getattr(self.call, "alias", None) != alias:
            call = copy.copy(self.call)
            call.alias = alias
            return call.to_sql()
        return self.call.to_sql()

class FunctionCall(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringPatternPredicateMixin,
    TypeCastingMixin,
    ResultTypeMixin,
    SQLValueExpression,
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
    SQLValueExpression,
):
    """Represents a SQL type cast as a proper AST node.

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
        expression: "SQLValueExpression",
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


class Subquery(AliasableMixin, ArithmeticMixin, ComparisonMixin, TypeCastingMixin, SQLValueExpression):
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
            elif is_sql_query_and_params(query):
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


class QualifiedIdentifierExpression(BaseExpression):
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
        self.name_need_quote = name_need_quote
        self.schema_need_quote = schema_need_quote
        self.schema = schema
        self.name = name


class WildcardExpression(SQLValueExpression):
    """Represents a wildcard expression (SELECT *) in a SQL query.

    Per-role quoting fields (all default to ``True``):
    - ``table_need_quote`` ↔ ``table``
    - ``schema_need_quote`` ↔ ``schema_name``
    """

    @property
    def format_method(self) -> str:
        return "format_wildcard"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: Optional[str] = None,
        schema_name: Optional[str] = None,
        table_need_quote: bool = True,
        schema_need_quote: bool = True,
    ):
        super().__init__(dialect)
        self.table_need_quote = table_need_quote
        self.schema_need_quote = schema_need_quote
        self.table = table
        self.schema_name = schema_name



