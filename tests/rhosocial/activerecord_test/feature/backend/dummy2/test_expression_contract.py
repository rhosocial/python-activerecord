# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_expression_contract.py
"""
Contract test: every built-in expression class must satisfy the
"__init__ parameter ↔ stored attribute" convention that powers the
introspection-based default implementation of BaseExpression.get_params().

For each registered expression class, an instance is constructed with
heuristic placeholder arguments, then get_params() is required to return
a value for every __init__ parameter (excluding self/dialect/**kwargs)
without emitting the "cannot find attribute" warning.

Classes that cannot be auto-constructed must be listed explicitly in
KNOWN_NON_AUTO_CONSTRUCTIBLE with a reason, so new violations fail loudly.
"""

import inspect
import typing
import warnings

import pytest

from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.serialization import ExpressionRegistry


# Classes that legitimately cannot be auto-constructed with heuristic
# fillers (e.g. require real backend objects). Any new entry must carry
# a justification.
KNOWN_NON_AUTO_CONSTRUCTIBLE = {
    # class FQN suffix : reason
}


def _special_constructors():
    """Explicit constructions for classes whose __init__ validation
    rejects heuristic placeholder values."""
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
        from rhosocial.activerecord.backend.expression.core import TableExpression
        return TableExpression(d, name)

    def partition_clause(d):
        return PartitionClause(d, method=PartitionStrategy.RANGE, keys=[Column(d, "created_at")])

    def on_conflict(d):
        return OnConflictClause(d, do_nothing=True, conflict_target=["id"])

    def update_expr(d):
        return UpdateExpression(d, table=_table(d), assignments={"a": Literal(d, 1)})

    return {
        "advanced_functions.JSONExpression": json_expr,
        "query_parts.JoinExpression": join_expr,
        "ddl_partition.PartitionClause": partition_clause,
        "dml.OnConflictClause": on_conflict,
        "dml.UpdateExpression": update_expr,
    }


def _placeholder_for(param: inspect.Parameter, dialect):
    """Return a heuristic construction value for a required parameter."""
    annotation = param.annotation
    if annotation is not inspect.Parameter.empty:
        try:
            hints = typing.get_type_hints(type("T", (), {}))
        except Exception:
            hints = {}
        del hints
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
    args = []
    kwargs = {}
    skipped_defaulted_positional = False
    for pname, param in sig.parameters.items():
        if pname in ("self", "dialect"):
            continue
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            continue
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            # Only fill varargs if no defaulted positional param was skipped;
            # otherwise the filler would land in that defaulted slot.
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
            return cls(dialect, *args, **kwargs)
    except Exception:
        return None


class TestInitParamAttributeContract:
    """For every registered expression class, get_params() must resolve
    every __init__ parameter without emitting the fallback warning."""

    def test_all_builtin_expressions(self, dummy_dialect):
        ExpressionRegistry._auto_register_builtins()
        specials = _special_constructors()
        skipped = []
        checked = 0
        for fqn, cls in sorted(ExpressionRegistry._registry.items()):
            if inspect.isabstract(cls):
                continue
            special = next((fn for s, fn in specials.items() if fqn.endswith(s)), None)
            if special is not None:
                instance = special(dummy_dialect)
            else:
                instance = _try_construct(cls, dummy_dialect)
            if instance is None:
                skipped.append(fqn)
                continue
            checked += 1
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                params = instance.get_params()
            missing_warnings = [
                w for w in caught if "cannot find attribute" in str(w.message)
            ]
            assert not missing_warnings, (
                f"{fqn}: get_params() could not resolve attributes: "
                f"{[str(w.message) for w in missing_warnings]}"
            )
            sig = inspect.signature(cls.__init__)
            for pname, param in sig.parameters.items():
                if pname in ("self", "dialect"):
                    continue
                if param.kind == inspect.Parameter.VAR_KEYWORD:
                    continue
                if pname not in params:
                    # Round-trip safe omission: a defaulted parameter whose
                    # current value equals its default may be omitted from
                    # get_params() (the deserializer restores the default).
                    assert param.default is not inspect.Parameter.empty, (
                        f"{fqn}: required __init__ parameter '{pname}' missing "
                        "from get_params() result"
                    )
                    attr = getattr(instance, f"_{pname}", getattr(instance, pname, None))
                    assert attr == param.default, (
                        f"{fqn}: __init__ parameter '{pname}' omitted from "
                        f"get_params() but its value {attr!r} != default "
                        f"{param.default!r}; round-trip would lose state"
                    )

        unexpected_skips = [
            fqn for fqn in skipped
            if not any(fqn.endswith(suffix) for suffix in KNOWN_NON_AUTO_CONSTRUCTIBLE)
        ]
        assert checked > 0, "no expression classes were auto-constructed"
        assert not unexpected_skips, (
            "Classes could not be auto-constructed (add to "
            "KNOWN_NON_AUTO_CONSTRUCTIBLE with a reason, or fix): "
            + ", ".join(unexpected_skips)
        )
