# tests/rhosocial/activerecord_test/feature/backend/expression_test_utils.py
"""
Shared helpers for expression serialization round-trip and contract tests.

These helpers construct expression instances from their class using either
heuristic placeholders (from the __init__ signature) or explicit
special-case constructors, so tests can exercise every registered expression
class in a backend-agnostic way.
"""

import inspect
import typing
import warnings

from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate


def _placeholder_for(param: inspect.Parameter, dialect):
    """Return a heuristic construction value for a required parameter."""
    annotation = param.annotation
    if annotation is not inspect.Parameter.empty:
        origin = typing.get_origin(annotation)
        raw = annotation if origin is None else origin
        if isinstance(annotation, str):
            text = annotation
        else:
            text = getattr(raw, "__name__", "")
        if raw in (list, tuple, set):
            return []
        if raw is dict:
            return {}
        if raw is str or "str" in text:
            return "x"
        if raw is int:
            return 1
        if raw is float:
            return 1.0
        if raw is bool:
            return True
        if "Expression" in text or "Subquery" in text:
            return Literal(dialect, 1)

    name = param.name
    if name in ("value",):
        return 1
    if name in ("values", "columns", "args", "params", "predicates", "expressions"):
        return []
    if name in ("left", "right") or "predicate" in name or "condition" in name:
        return ComparisonPredicate(dialect, "=", Column(dialect, "a"), Literal(dialect, 1))
    if "expression" in name or name in ("expr", "operand", "subquery", "query"):
        return Literal(dialect, 1)
    return "x"


def _try_construct(cls, dialect):
    """Construct an instance of cls with heuristic arguments; None on failure."""
    sig = inspect.signature(cls.__init__)
    # DataType value-object family declares dialect as an optional trailing
    # keyword (e.g. VarCharType(length=None, dialect=None)); standard
    # expressions declare it first. Detect the convention.
    first_param = next((p for p in sig.parameters if p != "self"), None)
    dialect_as_kw = first_param != "dialect"
    args = []
    kwargs = {}
    skipped_defaulted_positional = False
    for pname, param in sig.parameters.items():
        if pname in ("self", "dialect"):
            continue
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            continue
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            if not skipped_defaulted_positional:
                args.append(Literal(dialect, 1))
            continue
        if param.default is not inspect.Parameter.empty:
            if param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
                skipped_defaulted_positional = True
            continue
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            kwargs[pname] = _placeholder_for(param, dialect)
        else:
            args.append(_placeholder_for(param, dialect))
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if dialect_as_kw:
                return cls(*args, dialect=dialect, **kwargs)
            return cls(dialect, *args, **kwargs)
    except Exception:
        return None


def special_constructors():
    """Explicit constructions for classes whose __init__ validation
    rejects heuristic placeholder values. Keyed by class qualified name
    suffix (module.name)."""
    from rhosocial.activerecord.backend.expression.advanced_functions import JSONExpression
    from rhosocial.activerecord.backend.expression.query_parts import JoinExpression
    from rhosocial.activerecord.backend.expression.statements.ddl_partition import (
        PartitionClause,
        PartitionStrategy,
    )
    from rhosocial.activerecord.backend.expression.statements.dml import (
        OnConflictClause,
        UpdateExpression,
    )
    from rhosocial.activerecord.backend.expression.statements.ddl_view import (
        CreateViewExpression,
    )
    from rhosocial.activerecord.backend.expression.statements.dql import QueryExpression
    from rhosocial.activerecord.backend.expression.datetime import (
        DatePartExpression,
        DateTimeDiffExpression,
        DateTimeSubtractExpression,
        DateTimeAddExpression,
        DateTruncExpression,
        ExtractExpression,
        IntervalExpression,
    )
    from rhosocial.activerecord.backend.expression.core import TableExpression

    def json_expr(d):
        return JSONExpression(d, Literal(d, '{"a": 1}'), path="$.a")

    def join_expr(d):
        return JoinExpression(
            d,
            left_table=_table(d, "a"),
            right_table=_table(d, "b"),
            condition=ComparisonPredicate(d, "=", Column(d, "a"), Column(d, "b")),
        )

    def _table(d, name="t"):
        return TableExpression(d, name)

    def partition_clause(d):
        return PartitionClause(d, method=PartitionStrategy.RANGE, keys=[Column(d, "created_at")])

    def on_conflict(d):
        return OnConflictClause(d, do_nothing=True, conflict_target=["id"])

    def update_expr(d):
        return UpdateExpression(d, table=_table(d), assignments={"a": Literal(d, 1)})

    def create_view_expr(d):
        query = QueryExpression(d, select=[Column(d, "id")], from_=_table(d, "t"))
        return CreateViewExpression(d, view_name="v", query=query)

    def extract_expr(d):
        return ExtractExpression(d, "YEAR", Column(d, "created_at"))

    def datepart_expr(d):
        return DatePartExpression(d, "YEAR", Column(d, "created_at"))

    def datetrunc_expr(d):
        return DateTruncExpression(d, "year", Column(d, "created_at"))

    def interval_expr(d):
        return IntervalExpression(d, 7, "day")

    def datetime_diff_expr(d):
        return DateTimeDiffExpression(d, "day", Column(d, "a"), Column(d, "b"))

    def datetime_sub_expr(d):
        return DateTimeSubtractExpression(d, Column(d, "a"), IntervalExpression(d, 1, "day"))

    def datetime_add_expr(d):
        return DateTimeAddExpression(d, Column(d, "a"), IntervalExpression(d, 1, "day"))

    return {
        "advanced_functions.JSONExpression": json_expr,
        "query_parts.JoinExpression": join_expr,
        "statements.ddl_partition.PartitionClause": partition_clause,
        "statements.dml.OnConflictClause": on_conflict,
        "statements.dml.UpdateExpression": update_expr,
        "statements.ddl_view.CreateViewExpression": create_view_expr,
        "datetime.ExtractExpression": extract_expr,
        "datetime.DatePartExpression": datepart_expr,
        "datetime.DateTruncExpression": datetrunc_expr,
        "datetime.IntervalExpression": interval_expr,
        "datetime.DateTimeDiffExpression": datetime_diff_expr,
        "datetime.DateTimeSubtractExpression": datetime_sub_expr,
        "datetime.DateTimeAddExpression": datetime_add_expr,
    }


def make_instance(cls, dialect):
    """Best-effort construction for an expression class.

    Returns (instance, source) where source is "special", "heuristic", or
    (None, "failed").
    """
    specials = special_constructors()
    full_name = f"{cls.__module__}.{cls.__name__}"
    key = next((k for k in specials if full_name.endswith(k)), None)
    if key is not None:
        return specials[key](dialect), "special"
    instance = _try_construct(cls, dialect)
    if instance is None:
        return None, "failed"
    return instance, "heuristic"