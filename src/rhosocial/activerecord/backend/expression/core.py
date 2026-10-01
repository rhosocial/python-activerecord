# src/rhosocial/activerecord/backend/expression/core.py
"""
Core SQL expression components like columns, literals, function calls, and subqueries.
"""

from typing import Any, Tuple, Optional, Dict, TYPE_CHECKING, Union

from .bases import BaseExpression, SQLQueryAndParams, SQLValueExpression, is_sql_query_and_params
from .column_types import ColumnBase
from .mixins import (
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    IntegerValueMixin,
    JSONAccessorMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


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
    ArithmeticMixin,
    StringPatternPredicateMixin,
    JSONAccessorMixin,
    ColumnBase,
):
    """A column reference whose value type is not known.

    This is the **permissive** column: it keeps the full operation set and
    is a *sibling* of the type-narrowed classes in
    :mod:`...expression.column_types`, not their parent. Two reasons it
    survives rather than being replaced:

    * A column built by hand — ``Column(dialect, "settings")`` — has no model
      field behind it, so there is nothing to infer a type from. This is
      common in tests, in ``DerivedField`` callbacks and in backend examples.
    * A model field whose annotation cannot be classified (``Any``, an
      unresolvable ``Union``) must not lose operations it may well support.

    When the type *is* known, :class:`FieldProxy
    <rhosocial.activerecord.base.field_proxy.FieldProxy>` returns the
    matching narrow class instead — ``User.c.age`` is a
    :class:`~...expression.column_types.NumericColumn` and offers no
    ``.like()``, while a hand-built ``Column`` still does. The class identity
    of a typed column does not vary by backend; only its storage does.
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
            value_type=None,
        )


class IntegerValueExpression(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    IntegerValueMixin,
    StringPatternPredicateMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """An integer-valued expression that is not a column reference.

    Returned by the string operations whose result is a number — ``length``,
    ``ascii``, ``strpos``, ``position``, ``octet_length``, ``bit_length`` — so
    that ``col.length() > 5`` reads naturally and ``col.length().upper()``
    fails, which it should: there is no such thing as an upper-cased length.

    It carries :class:`ArithmeticMixin`, so integer arithmetic is available
    and stays an integer. It carries the pattern predicates because any value
    can be compared or matched, not because a number is text.
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
        return self.call.to_sql()

    def __getattr__(self, name):
        """Forward unknown attributes to the wrapped call.

        Args:
            name: Attribute name not found on this wrapper.

        Returns:
            The attribute from the wrapped function call.
        """
        if name == "call":
            raise AttributeError(name)
        return getattr(self.__dict__["call"], name)



class StringValueExpression(
    AliasableMixin,
    ComparisonMixin,
    IntegerValueMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
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

    The class mirrors :class:`~...expression.advanced_functions.JSONExpression`,
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
        return self.call.to_sql()

    def __getattr__(self, name):
        """Forward unknown attributes to the wrapped call.

        Function calls carry dialect-level state that renderers and callers
        read (``niladic``, and whatever a backend attaches). Delegating keeps
        this wrapper transparent instead of a second, drifting copy.

        Args:
            name: Attribute name not found on this wrapper.

        Returns:
            The attribute from the wrapped function call.
        """
        if name == "call":
            raise AttributeError(name)
        return getattr(self.__dict__["call"], name)



class FunctionCall(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringPatternPredicateMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """Represents a scalar SQL function call, such as LOWER, CONCAT, etc.

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
    ):
        super().__init__(dialect)
        self.func_name = func_name
        self.args = list(args)
        self.is_distinct = is_distinct
        self.alias = alias
        self.niladic = niladic


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
    ``expr.cast("A").cast("B")`` renders ``CAST(CAST(expr AS A) AS B)``.
    When the wrapped expression carries an alias, ``cast()`` hoists the
    alias onto the new node (the alias decorates the outermost rendered
    form), so ``col.cast("INTEGER").as_("v")`` and
    ``col.as_("v").cast("INTEGER")`` both render
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
        target_type: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
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


class TableExpression(AliasableMixin, BaseExpression):
    """Represents a table or view in a SQL query, optionally with schema and alias.

    Per-role quoting fields (all default to ``True``):
    - ``name_need_quote`` ↔ ``name``
    - ``schema_need_quote`` ↔ ``schema_name``
    - ``alias_need_quote`` ↔ ``alias``
    """

    @property
    def format_method(self) -> str:
        return "format_table"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        schema_name: Optional[str] = None,
        alias: Optional[str] = None,
        temporal_options: Optional[Dict[str, Any]] = None,
        name_need_quote: bool = True,
        alias_need_quote: bool = True,
        schema_need_quote: bool = True,
    ):
        super().__init__(dialect)
        self.name_need_quote = name_need_quote
        self.alias_need_quote = alias_need_quote
        self.schema_need_quote = schema_need_quote
        self.name = name
        self.schema_name = schema_name
        self.alias = alias
        self.temporal_options = temporal_options or {}


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



