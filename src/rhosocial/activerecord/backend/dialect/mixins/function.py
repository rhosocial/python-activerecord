# src/rhosocial/activerecord/backend/dialect/mixins/function.py
"""Function-related dialect mixins.

Contains :class:`FunctionCallMixin` for rendering scalar/aggregate function
*call* expressions in queries, and :class:`FunctionMixin` for SQL/PSM
function *DDL* (``CREATE FUNCTION`` / ``DROP FUNCTION``).
"""
import re
from typing import Any, Dict, List, Tuple, TYPE_CHECKING

from ...expression.objects import Function

if TYPE_CHECKING:  # pragma: no cover
    from ...expression import bases
    from ...expression.statements import (
        CreateFunctionStatement,
        DropFunctionStatement,
    )


class FunctionCallMixin:
    """Mixin for formatting scalar and aggregate function call expressions.

    Distinct from :class:`FunctionMixin`, which covers SQL/PSM function DDL
    (``CREATE FUNCTION`` / ``DROP FUNCTION``). Call formatting is a query
    expression concern and is therefore composed into
    :class:`~.expression.ExpressionMixin`.
    """

    def format_function_call(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Format a function call expression, scalar or aggregate.

        Renders ``NAME(args)`` with optional ``DISTINCT``, a trailing
        ``FILTER (WHERE ...)`` clause and a trailing ``OVER (...)`` window
        clause, in that order, followed by ``AS alias``. ``COUNT(*)`` is
        special-cased so that a wildcard argument renders as ``*``. Niladic
        functions with no arguments and no ``DISTINCT`` omit the parentheses.
        Every argument must be an expression: a bare value fails to render
        rather than being turned into a bind parameter here, because the
        renderer does not decide what a caller meant. A value goes through
        :class:`~...expression.core.Literal` at the call site.

        The first thing it does is refuse a call this dialect's version
        predates (:meth:`~.base.SQLDialectBase.check_function_version`), so a
        backend that records a floor for the name gets the refusal instead of
        SQL the server will reject.

        Args:
            expr: The function call expression to render.

        Returns:
            A ``(sql, params)`` tuple.

        Raises:
            UnsupportedFeatureError: If a ``FILTER`` clause is requested on a
                dialect that does not support it, an ``OVER`` clause is
                requested on a dialect that does not support window
                functions, or the dialect records a version floor for this
                function that its version is below.
        """
        from ...expression import core, operators
        from ..protocols import FilterClauseSupport, WindowFunctionSupport

        self.check_function_version(expr.func_name)

        if (
            expr.func_name.upper() == "COUNT"
            and len(expr.args) == 1
            and (
                (isinstance(expr.args[0], operators.RawSQL) and expr.args[0].expression == "*")
                or isinstance(expr.args[0], core.RowCountWildcard)
            )
        ):
            args_sql = ["*"]
            args_params = []
        else:
            args_sql = []
            args_params = []
            for arg in expr.args:
                # A factory that accepts a bare value is deciding what it
                # meant; the renderer refuses instead of manufacturing the
                # Literal the caller should have written (see the docstring).
                sql_part, params_part = arg.to_sql()
                args_sql.append(sql_part)
                args_params.append(params_part)

        distinct = "DISTINCT " if expr.is_distinct else ""
        args_sql_str = ", ".join(args_sql)

        if expr.niladic and not args_sql and not distinct:
            func_call_sql = expr.func_name.upper()
        else:
            func_call_sql = f"{expr.func_name.upper()}({distinct}{args_sql_str})"

        all_params: List[Any] = []
        for param_tuple in args_params:
            all_params.extend(param_tuple)

        filter_predicate = expr.filter_predicate
        if filter_predicate:
            if isinstance(self, FilterClauseSupport) and self.supports_filter_clause():
                from ...expression.statements.filter_clause import FilterClause
                filter_expr = FilterClause(self, condition=filter_predicate)
                filter_clause_sql, filter_clause_params = self.format_filter_clause(filter_expr)
                func_call_sql += f" {filter_clause_sql}"
                all_params.extend(filter_clause_params)
            else:
                from ..exceptions import UnsupportedFeatureError
                raise UnsupportedFeatureError(
                    self.name,
                    "FILTER clause in aggregate functions",
                    "Use a CASE expression inside the aggregate function instead.",
                )

        window_spec = expr.window_spec
        if window_spec is not None:
            # Checked as a protocol, like the FILTER clause above: a dialect
            # that does not compose WindowFunctionSupport has neither the probe
            # nor the formatter, and must refuse the clause rather than fail
            # resolving a method.
            if not isinstance(self, WindowFunctionSupport) or not self.supports_window_functions():
                from ..exceptions import UnsupportedFeatureError
                raise UnsupportedFeatureError(self.name, "window functions")
            if isinstance(window_spec, str):
                # Reference to a named window definition.
                window_part = self.format_identifier(window_spec)
            else:
                window_spec_sql, window_spec_params = self.format_window_specification(window_spec)
                window_part = f"({window_spec_sql})" if window_spec_sql else "()"
                all_params.extend(window_spec_params)
            func_call_sql = f"{func_call_sql} OVER {window_part}"

        if expr.alias:
            func_call_sql = f"{func_call_sql} AS {self.format_identifier(expr.alias)}"

        return func_call_sql, tuple(all_params)


    # ------------------------------------------------------------------
    # Standard function nodes (catalog §3.4): one entry point per node kind.
    # ------------------------------------------------------------------

    def _format_aggregate_function(self, name: str, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``NAME(operand)`` / ``NAME(DISTINCT operand)`` for an aggregate.

        The operand is the node's contract field; ``COUNT(*)`` is the one place
        the row-count wildcard is legal, and it renders as the bare ``*`` rather
        than going through ``to_sql``.
        """
        from ...expression.core import RowCountWildcard

        if isinstance(expr.operand, RowCountWildcard):
            operand_sql, operand_params = "*", ()
        else:
            operand_sql, operand_params = expr.operand.to_sql()
        distinct = "DISTINCT " if expr.distinct else ""
        sql = f"{name}({distinct}{operand_sql})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, tuple(operand_params)

    def _format_scalar_function(self, name: str, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``NAME(operand)`` for a one-argument scalar function node."""
        operand_sql, operand_params = expr.operand.to_sql()
        sql = f"{name}({operand_sql})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, tuple(operand_params)

    def _format_window_rank(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render a ranking window function: a name, empty parentheses, maybe an alias."""
        sql = f"{expr.function_name}()"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, ()

    def format_row_number_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``ROW_NUMBER()``."""
        return self._format_window_rank(expr)

    def format_rank_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``RANK()``."""
        return self._format_window_rank(expr)

    def format_dense_rank_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``DENSE_RANK()``."""
        return self._format_window_rank(expr)

    def format_json_objectagg_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``JSON_OBJECTAGG(key, value)``.

        Written here rather than through the shared aggregate renderer because
        this aggregate has two operands and that one expects the node's single
        ``operand``; ``DISTINCT`` does not apply either, since two distinct
        pairs are still distinct pairs.
        """
        key_sql, key_params = expr.operand.to_sql()
        value_sql, value_params = expr.entry_value.to_sql()
        sql = f"JSON_OBJECTAGG({key_sql}, {value_sql})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, tuple(key_params) + tuple(value_params)

    def format_json_arrayagg_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``JSON_ARRAYAGG([DISTINCT] value)``."""
        return self._format_aggregate_function("JSON_ARRAYAGG", expr)

    def format_absolute_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``ABSOLUTE(...)`` from the node's own operand list."""
        return self._format_function(expr.function_name, expr, expr.arguments)

    def format_round_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``ROUND(...)`` from the node's own operand list."""
        return self._format_function(expr.function_name, expr, expr.arguments)

    def format_ceil_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``CEIL(...)`` from the node's own operand list."""
        return self._format_function(expr.function_name, expr, expr.arguments)

    def format_floor_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``FLOOR(...)`` from the node's own operand list."""
        return self._format_function(expr.function_name, expr, expr.arguments)

    def format_truncate_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``TRUNCATE(...)`` from the node's own operand list."""
        return self._format_function(expr.function_name, expr, expr.arguments)

    def format_square_root_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``SQUARE ROOT(...)`` from the node's own operand list."""
        return self._format_function(expr.function_name, expr, expr.arguments)

    def format_power_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``POWER(...)`` from the node's own operand list."""
        return self._format_function(expr.function_name, expr, expr.arguments)

    def format_exponential_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``EXPONENTIAL(...)`` from the node's own operand list."""
        return self._format_function(expr.function_name, expr, expr.arguments)

    def format_logarithm_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``LOGARITHM(...)`` from the node's own operand list."""
        return self._format_function(expr.function_name, expr, expr.arguments)

    def format_sine_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``SINE(...)`` from the node's own operand list."""
        return self._format_function(expr.function_name, expr, expr.arguments)

    def format_cosine_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``COSINE(...)`` from the node's own operand list."""
        return self._format_function(expr.function_name, expr, expr.arguments)

    def format_tangent_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``TANGENT(...)`` from the node's own operand list."""
        return self._format_function(expr.function_name, expr, expr.arguments)

    def format_modulo_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``MODULO(...)`` from the node's own operand list."""
        return self._format_function(expr.function_name, expr, expr.arguments)

    def format_sign_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``SIGN(...)`` from the node's own operand list."""
        return self._format_function(expr.function_name, expr, expr.arguments)

    def format_array_agg_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``ARRAY_AGG([DISTINCT] operand)``."""
        return self._format_aggregate_function("ARRAY_AGG", expr)

    def format_count_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``COUNT(*)`` or ``COUNT([DISTINCT] operand)``."""
        return self._format_aggregate_function("COUNT", expr)

    def format_sum_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``SUM([DISTINCT] operand)``."""
        return self._format_aggregate_function("SUM", expr)

    def format_avg_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``AVG([DISTINCT] operand)``."""
        return self._format_aggregate_function("AVG", expr)

    def format_min_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``MIN([DISTINCT] operand)``."""
        return self._format_aggregate_function("MIN", expr)

    def format_max_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``MAX([DISTINCT] operand)``."""
        return self._format_aggregate_function("MAX", expr)

    def format_upper_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``UPPER(operand)``."""
        return self._format_scalar_function("UPPER", expr)

    def format_lower_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``LOWER(operand)``."""
        return self._format_scalar_function("LOWER", expr)

    def format_char_length_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``CHAR_LENGTH(operand)`` — the spelling here is ``LENGTH``.

        ``expr.unit`` is deliberately **not read**: it records which length
        semantics the caller asked for (characters / octets / bits), and this
        formatter writes the spelling the standard spelling uses. A backend
        whose ``LENGTH`` answers a different question (MySQL / ClickHouse
        count bytes, SQL Server counts UTF-16 units) overrides this entry
        point rather than having the core pick a unit for it.
        """
        return self._format_scalar_function("LENGTH", expr)

    def _format_niladic_function(self, name: str, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render a niladic function as the bare keyword.

        The standard writes these without parentheses (``CURRENT_USER``), but
        the parentheses are not universal: MySQL's ``NOW`` requires them while
        its ``CURRENT_TIMESTAMP`` may omit them, and SQL Server is the other way
        round for its own pair. So the node carries no arguments and the
        spelling -- with or without ``()`` -- is decided here, per backend.
        """
        sql = name.upper()
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, ()

    def format_current_user_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``CURRENT_USER``."""
        return self._format_niladic_function("CURRENT_USER", expr)

    def format_session_user_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``SESSION_USER``."""
        return self._format_niladic_function("SESSION_USER", expr)

    def format_system_user_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``SYSTEM_USER``."""
        return self._format_niladic_function("SYSTEM_USER", expr)

    def format_declared_result(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render a declared-result annotation by rendering what it annotates.

        The node underneath is left exactly as it was: the statement was already
        correct and only the knowledge of what it yields was missing, so the SQL
        is the annotated node's SQL unchanged. An alias rides along, because a
        column given a name here is a name the caller asked for.
        """
        source_sql, source_params = expr.source.to_sql()
        if expr.source.alias and not expr.alias:
            return source_sql, tuple(source_params)
        if expr.alias:
            return f"{source_sql} AS {self.format_identifier(expr.alias)}", tuple(source_params)
        return source_sql, tuple(source_params)

    def format_concat_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``CONCAT(a, b, ...)``.

        A backend whose ``CONCAT`` ignores NULL, or treats it as an empty
        string, overrides this: the standard says NULL, and ``||`` is the
        spelling to reach for when concatenating may skip an operand.
        """
        return self._format_function("CONCAT", expr, expr.operands)

    def format_coalesce_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``COALESCE(a, b, ...)``."""
        return self._format_function("COALESCE", expr, expr.operands)

    def format_substring_expression(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``SUBSTRING(text FROM start [FOR length])``.

        The base spells it as a plain call, which is what most backends accept
        and what the pre-node formatter produced. Backends wanting the
        standard's ``FROM`` / ``FOR`` keywords override this.
        """
        return self._format_optional_length_function(
            "SUBSTRING", expr, expr.target, expr.start, expr.length
        )

    def format_overlay_expression(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``OVERLAY(text, replacement, start [, length])``."""
        return self._format_optional_length_function(
            "OVERLAY", expr, expr.target, expr.replacement, expr.start, expr.length
        )

    def format_position_expression(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render the position of a substring, in whichever spelling was asked.

        The two spellings put the operands in opposite orders, which is the
        whole reason they are one node: ``STRPOS(haystack, needle)`` and
        ``POSITION(needle IN haystack)`` ask the same question and read it
        differently. The node always holds (haystack, needle); only this
        formatter knows which way round the SQL wants them.
        """
        haystack_sql, haystack_params = expr.haystack.to_sql()
        needle_sql, needle_params = expr.needle.to_sql()
        # Ordered as they are written, so the bind values follow the
        # placeholders: POSITION reverses the operands and must reverse the
        # parameters with them, or a two-literal call binds them swapped.
        if expr.spelling == "POSITION":
            args_sql, args_params = [needle_sql, haystack_sql], [needle_params, haystack_params]
        else:
            args_sql, args_params = [haystack_sql, needle_sql], [haystack_params, needle_params]
        sql = f"{expr.spelling}({', '.join(args_sql)})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        ordered_params: List[Any] = []
        for part in args_params:
            ordered_params.extend(part)
        return sql, tuple(ordered_params)

    def format_replace_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``REPLACE(text, pattern, replacement)``."""
        return self._format_function(
            "REPLACE", expr, (expr.target, expr.pattern, expr.replacement)
        )

    def format_initcap_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``INITCAP(text)``."""
        return self._format_function("INITCAP", expr, (expr.target,))

    def format_left_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``LEFT(text, n)``."""
        return self._format_function("LEFT", expr, (expr.target, expr.count))

    def format_right_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``RIGHT(text, n)``."""
        return self._format_function("RIGHT", expr, (expr.target, expr.count))

    def format_reverse_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``REVERSE(text)``."""
        return self._format_function("REVERSE", expr, (expr.target,))

    def format_translate_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``TRANSLATE(text, from, to)``."""
        return self._format_function(
            "TRANSLATE", expr, (expr.target, expr.from_chars, expr.to_chars)
        )

    def format_space_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``SPACE(n)``."""
        return self._format_function("SPACE", expr, (expr.count,))

    def format_chr_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``CHR(code)``."""
        return self._format_function("CHR", expr, (expr.code,))

    def format_ascii_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``ASCII(text)``."""
        return self._format_function("ASCII", expr, (expr.target,))

    def format_octet_length_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``OCTET_LENGTH(text)``."""
        return self._format_function("OCTET_LENGTH", expr, (expr.target,))

    def format_bit_length_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``BIT_LENGTH(text)``."""
        return self._format_function("BIT_LENGTH", expr, (expr.target,))

    # -- nodes with declared operands, rendered by name -----------------------

    def format_to_char_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``TO_CHAR(value[, format])`` -- text.

        The *format* operand is optional and its absence is the difference
        between a backend's default rendering and an explicit mask, so it is
        dropped from the SQL rather than sent as NULL.
        """
        operands = [expr.target]
        if expr.format is not None:
            operands.append(expr.format)
        return self._format_function("TO_CHAR", expr, operands)

    def format_to_number_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``TO_NUMBER(value[, format])`` -- a number."""
        operands = [expr.target]
        if expr.format is not None:
            operands.append(expr.format)
        return self._format_function("TO_NUMBER", expr, operands)

    def format_to_date_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``TO_DATE(value[, format])`` -- a **date**.

        Not a timestamp: every backend's ``TO_DATE`` answers with a calendar
        date, and claiming a timestamp would offer time-of-day operations on a
        value that has none.
        """
        operands = [expr.target]
        if expr.format is not None:
            operands.append(expr.format)
        return self._format_function("TO_DATE", expr, operands)

    def format_unnest_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``UNNEST(array)`` -- one row per element."""
        return self._format_function("UNNEST", expr, (expr.target,))

    def format_array_length_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``ARRAY_LENGTH(array[, dimension])`` -- a count."""
        operands = [expr.target]
        if expr.dimension is not None:
            operands.append(expr.dimension)
        return self._format_function("ARRAY_LENGTH", expr, operands)

    def format_json_build_object_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``JSON_BUILD_OBJECT(key, value, ...)`` -- pairs, in order."""
        return self._format_function("JSON_BUILD_OBJECT", expr, expr.pairs)

    def format_json_array_elements_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Render ``JSON_ARRAY_ELEMENTS(json)`` -- the array's elements, one per row."""
        return self._format_function("JSON_ARRAY_ELEMENTS", expr, (expr.target,))

    def _format_function(self, name: str, expr: "bases.BaseExpression", operands) -> Tuple[str, tuple]:
        """Render ``NAME(a, b, ...)`` from a node's operands.

        The one arity-agnostic renderer, for every function node whose
        parameters are a list or a fixed tuple. Nodes with a single ``operand``
        use :meth:`_format_scalar_function` instead, which reads that attribute
        directly.
        """
        parts_sql, parts_params = [], []
        for operand in operands:
            operand_sql, operand_params = operand.to_sql()
            parts_sql.append(operand_sql)
            parts_params.extend(operand_params)
        sql = f"{name.upper()}({', '.join(parts_sql)})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, tuple(parts_params)

    def _format_optional_length_function(
        self, name: str, expr: "bases.BaseExpression", *operands
    ) -> Tuple[str, tuple]:
        """Render ``NAME(...)`` where a trailing ``length`` operand is optional.

        The last operand is dropped from the SQL when it is ``None``, which is
        how ``SUBSTRING(x FROM 2)`` stays distinct from ``SUBSTRING(x FROM 2 FOR
        0)`` -- an explicit zero length is a real request for the empty string.
        """
        operands = list(operands)
        if operands and operands[-1] is None:
            operands.pop()
        return self._format_function(name, expr, operands)



class FunctionMixin:
    """Format SQL/PSM function DDL statements (CREATE FUNCTION / DROP FUNCTION).

    Capability probes default to ``False`` and are overridden by dialects that
    support user-defined functions.
    """

    def supports_function(self) -> bool:
        """Whether user-defined functions are supported (defaults to False)."""
        return False

    def supports_create_function(self) -> bool:
        """Whether CREATE FUNCTION is supported (defaults to False)."""
        return False

    def supports_drop_function(self) -> bool:
        """Whether DROP FUNCTION is supported (defaults to False)."""
        return False

    def supports_function_or_replace(self) -> bool:
        """Whether CREATE OR REPLACE FUNCTION is supported (defaults to False)."""
        return False

    def supports_function_parameters(self) -> bool:
        """Whether function parameter lists are supported (defaults to False)."""
        return False

    def supports_drop_function_if_exists(self) -> bool:
        """Whether DROP FUNCTION IF EXISTS is supported (defaults to False)."""
        return False

    def supports_drop_function_cascade(self) -> bool:
        """Whether DROP FUNCTION CASCADE is supported (defaults to False)."""
        return False

    def supports_drop_function_restrict(self) -> bool:
        """Whether DROP FUNCTION RESTRICT is supported (defaults to False)."""
        return False

    def supports_functions(self) -> Dict[str, bool]:
        """Return supported SQL functions as function_name -> bool mapping.

        Default implementation returns empty dict. Subclasses should override
        to provide actual function list from both core and backend-specific sources.

        Returns:
            Dict mapping function names to True/False. Default: empty dict.
        """
        return {}

    def format_create_function_statement(self, expr: "CreateFunctionStatement") -> Tuple[str, tuple]:
        """Format a CREATE FUNCTION statement per SQL/PSM.

        Args:
            expr: The CreateFunctionStatement to render.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            TypeError: ``CreateFunctionStatement.function`` is not a Function.
            Another object kind would have had its own name rendered as the
            function's.
            UnsupportedFeatureError: If the dialect does not support functions.
            ValueError: If a parameter or return type contains invalid
                characters.
        """
        if not isinstance(expr.function, Function):
            raise TypeError(
                f"CreateFunctionStatement.function must be a Function, "
                f"got {type(expr.function).__name__}"
            )
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_function():
            raise UnsupportedFeatureError(self.name, "functions")

        parts = ["CREATE FUNCTION"]

        if expr.or_replace:
            if not self.supports_function_or_replace():
                raise UnsupportedFeatureError(
                    self.name, "CREATE OR REPLACE FUNCTION",
                    f"{self.name} does not support CREATE OR REPLACE FUNCTION."
                )
            parts.insert(1, "OR REPLACE")

        parts.append(expr.function.to_sql()[0])

        if expr.parameters:
            if not self.supports_function_parameters():
                raise UnsupportedFeatureError(
                    self.name, "CREATE FUNCTION parameters",
                    f"{self.name} does not support CREATE FUNCTION parameters."
                )
            param_strs = []
            for p in expr.parameters:
                name = p.get("name", "")
                param_type = p.get("type", "")
                if name and param_type:
                    # Validate parameter name and type.
                    param_name = self.format_identifier(name)
                    if not re.fullmatch(r"[A-Za-z0-9\s(),]+", param_type):
                        raise ValueError(f"Invalid parameter type '{param_type}'")
                    param_strs.append(f"{param_name} {param_type}")
                elif param_type:
                    param_strs.append(param_type)
            parts.append(f"({', '.join(param_strs)})")
        else:
            parts.append("()")

        if expr.returns:
            # Validate return type.
            if not re.fullmatch(r"[A-Za-z0-9\s(),]+", expr.returns):
                raise ValueError(f"Invalid return type '{expr.returns}'")
            parts.append(f"RETURNS {expr.returns}")

        if expr.language:
            parts.append(f"LANGUAGE {expr.language}")

        if expr.body:
            parts.append("AS")
            parts.append(f"$${expr.body}$$")

        return " ".join(parts), ()

    def format_drop_function_statement(self, expr: "DropFunctionStatement") -> Tuple[str, tuple]:
        """Format a DROP FUNCTION statement per SQL/PSM.

        Args:
            expr: The DropFunctionStatement to render.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            TypeError: ``DropFunctionStatement.function`` is not a Function.
            Another object kind would have had its own name rendered as the
            function's.
            UnsupportedFeatureError: If the dialect does not support functions.
        """
        if not isinstance(expr.function, Function):
            raise TypeError(
                f"DropFunctionStatement.function must be a Function, "
                f"got {type(expr.function).__name__}"
            )
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_function():
            raise UnsupportedFeatureError(self.name, "functions")

        parts = ["DROP FUNCTION"]

        if expr.if_exists:
            if not self.supports_drop_function_if_exists():
                raise UnsupportedFeatureError(
                    self.name, "DROP FUNCTION IF EXISTS",
                    f"{self.name} does not support DROP FUNCTION IF EXISTS."
                )
            parts.append("IF EXISTS")

        parts.append(expr.function.to_sql()[0])

        if expr.parameters:
            param_types = ", ".join(expr.parameters)
            parts.append(f"({param_types})")

        if expr.cascade:
            if not self.supports_drop_function_cascade():
                raise UnsupportedFeatureError(
                    self.name, "DROP FUNCTION CASCADE",
                    f"{self.name} does not support DROP FUNCTION CASCADE."
                )
            parts.append("CASCADE")
        elif expr.restrict:
            if not self.supports_drop_function_restrict():
                raise UnsupportedFeatureError(
                    self.name, "DROP FUNCTION RESTRICT",
                    f"{self.name} does not support DROP FUNCTION RESTRICT."
                )
            parts.append("RESTRICT")

        return " ".join(parts), ()
