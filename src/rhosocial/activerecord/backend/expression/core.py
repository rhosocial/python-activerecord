# src/rhosocial/activerecord/backend/expression/core.py
"""
Core SQL expression components like columns, literals, function calls, and subqueries.
"""

from typing import Any, Tuple, Optional, Dict, TYPE_CHECKING, Union

from .bases import BaseExpression, SQLQueryAndParams, SQLValueExpression, is_sql_query_and_params
from .mixins import (
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringMixin,
    TypeCastingMixin,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class Literal(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringMixin,
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
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """Represents a column in a SQL query."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_column"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        table: Optional[str] = None,
        alias: Optional[str] = None,
        schema_name: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.name = name
        self.table = table
        self.alias = alias
        self.schema_name = schema_name


class FunctionCall(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringMixin,
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
    StringMixin,
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

    Supports SQL standard schema-qualified table names (schema_name.table_name).
    All major databases support this syntax.

    Args:
        dialect: The SQL dialect to use for formatting
        name: The table or view name
        schema_name: Optional schema/database name qualifier (SQL standard)
        alias: Optional table alias
        temporal_options: Optional temporal table options (e.g., FOR SYSTEM_TIME)

    Examples:
        # Simple table reference
        TableExpression(dialect, "users")
        # -> users

        # Schema-qualified table
        TableExpression(dialect, "users", schema_name="public")
        # -> public.users

        # With alias
        TableExpression(dialect, "users", alias="u")
        # -> users AS u

        # Schema-qualified with alias
        TableExpression(dialect, "users", schema_name="public", alias="u")
        # -> public.users AS u
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        schema_name: Optional[str] = None,
        alias: Optional[str] = None,
        temporal_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.name = name
        self.schema_name = schema_name
        self.alias = alias
        self.temporal_options = temporal_options or {}


class QualifiedIdentifierExpression(BaseExpression):
    """Represents a schema-qualified identifier (e.g., schema.table_name, schema.function_name).

    This is a general-purpose expression for any schema.name reference.
    Rendering delegates to the dialect's ``format_qualified_identifier``,
    which decides how identifiers are quoted.

    Attributes:
        schema: Optional schema/namespace qualifier.
        name: The identifier name.

    Example:
        >>> from rhosocial.activerecord.backend.impl.dummy import DummyDialect
        >>> dialect = DummyDialect()
        >>> qi = QualifiedIdentifierExpression(dialect, schema="partman", name="create_parent")
        >>> qi.to_sql()
        ('partman.create_parent', ())
        >>> qi2 = QualifiedIdentifierExpression(dialect, schema=None, name="create_parent")
        >>> qi2.to_sql()
        ('create_parent', ())
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_qualified_identifier"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        schema: Optional[str] = None,
        name: str = "",
    ):
        super().__init__(dialect)
        self.schema = schema
        self.name = name


class WildcardExpression(SQLValueExpression):
    """Represents a wildcard expression (SELECT *) in a SQL query.

    Important: When constructing queries that include wildcards (SELECT *),
    use WildcardExpression instead of Literal("*") to avoid treating the
    wildcard as a parameter value. Using Literal("*") will incorrectly
    include the '*' character in the parameter tuple rather than as part
    of the SQL query itself.

    Examples:
        # Correct usage:
        select=[WildcardExpression(dialect)]
        # Results in: SELECT * FROM ...

        # Incorrect usage:
        select=[Literal(dialect, "*")]
        # Results in: SELECT ? FROM ... with params ('*',)
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_wildcard"

    def __init__(self, dialect: "SQLDialectBase", table: Optional[str] = None, schema_name: Optional[str] = None):
        super().__init__(dialect)
        self.table = table  # Optional table qualifier for SELECT table.*
        self.schema_name = schema_name  # Optional schema qualifier for SELECT schema.table.*
