# src/rhosocial/activerecord/backend/expression/roundtrip_testing.py
"""
Reusable serialization round-trip testing helpers for expression packages.

Backend test suites (and the core suite) use this to exercise every
expression class in a given package subtree:

    from rhosocial.activerecord.backend.expression import (
        register_expressions_in_package,
        roundtrip_through_all_encodings,
    )

A backend-specific test then scans ``impl.<backend>.expression``, registers
each class into :class:`ExpressionRegistry` (so deserialization can find it),
constructs an instance, and asserts the spec round-trips through the dict /
JSON / XML encodings with ``get_params()`` equality and ``to_sql()``
consistency where the selected dialect supports it.
"""

import importlib
import inspect
import pkgutil
import warnings
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Type

from .bases import BaseExpression
from .serialization import (
    ExpressionRegistry,
    deserialize,
    deserialize_json,
    deserialize_xml,
    serialize,
    serialize_json,
    serialize_xml,
)

# (module-name-suffix, factory(dialect)->expr) keyed by the class's FQN suffix.
BACKEND_SPECIAL_CONSTRUCTORS: Dict[str, Callable] = {}


def register_special_constructor(fqn_suffix: str, factory: Callable) -> None:
    """Register an explicit constructor for a backend expression class.

    ``fqn_suffix`` matches against the class's full FQN (e.g.
    ``"show.expressions.ShowColumnsExpression"``). The factory receives the
    dialect and must return an expression instance.
    """
    BACKEND_SPECIAL_CONSTRUCTORS[fqn_suffix] = factory


def collect_expression_classes(package_path: str) -> Dict[str, Type[BaseExpression]]:
    """Walk a package subtree and collect every defined BaseExpression subclass.

    Returns ``{fqn: class}`` where ``fqn`` is ``module.ClassName``.
    Reflects the actual submodule that defines the class (via
    ``obj.__module__ == modname``) so re-exported references are not captured.
    """
    pkg = importlib.import_module(package_path)
    classes: Dict[str, Type[BaseExpression]] = {}
    for _, modname, _ in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
        try:
            mod = importlib.import_module(modname)
        except Exception:
            continue
        for name in dir(mod):
            obj = getattr(mod, name, None)
            if (
                isinstance(obj, type)
                and obj.__module__ == modname
                and issubclass(obj, BaseExpression)
                and obj is not BaseExpression
                and not inspect.isabstract(obj)
            ):
                classes[f"{modname}.{name}"] = obj
    return classes


def placeholder_for(param: inspect.Parameter) -> Any:
    """Return a heuristic construction value for a required parameter."""
    annotation = param.annotation
    if annotation is not inspect.Parameter.empty:
        text = annotation if isinstance(annotation, str) else getattr(annotation, "__name__", "")
        if "Expression" in text or "Subquery" in text or "Clause" in text:
            return None  # caller substitutes expression node
        if "str" in text:
            return "x"
        if "int" in text:
            return 1
        if "float" in text:
            return 1.0
        if "bool" in text:
            return True
    name = param.name
    if name in ("value",):
        return 1
    if name in ("values", "columns", "args", "params", "predicates", "expressions"):
        return []
    if "expression" in name or name in ("expr", "operand", "subquery", "query"):
        return None
    return "x"


def last_resort_construct(cls: Type[BaseExpression], dialect: Any) -> Optional[BaseExpression]:
    """Heuristic construction; returns None on failure (or on missing symbols)."""
    from .core import Column, Literal
    from .predicates import ComparisonPredicate

    sig = inspect.signature(cls.__init__)
    args = []
    kwargs = {}
    # DataType-family declares dialect as trailing keyword.
    first_param = next((p for p in sig.parameters if p != "self"), None)
    dialect_as_kw = first_param != "dialect"
    for pname, param in sig.parameters.items():
        if pname in ("self", "dialect"):
            continue
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            continue
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            args.append(Literal(dialect, 1))
            continue
        if param.default is not inspect.Parameter.empty:
            continue
        ph = placeholder_for(param)
        if ph is None:
            if pname in ("left", "right") or "predicate" in pname or "condition" in pname:
                ph = ComparisonPredicate(dialect, "=", Column(dialect, "a"), Literal(dialect, 1))
            else:
                ph = Literal(dialect, 1)
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            kwargs[pname] = ph
        else:
            args.append(ph)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if dialect_as_kw:
                return cls(*args, dialect=dialect, **kwargs)
            return cls(dialect, *args, **kwargs)
    except Exception:
        return None


def construct_expression(fqn: str, cls: Type[BaseExpression], dialect: Any):
    """Best-effort construction. Returns (instance, source) or (None, reason)."""
    special = BACKEND_SPECIAL_CONSTRUCTORS.get(
        next((s for s in BACKEND_SPECIAL_CONSTRUCTORS if fqn.endswith(s)), "")
    )
    if special is not None:
        return special(dialect), "special"
    instance = last_resort_construct(cls, dialect)
    if instance is None:
        return None, "heuristic-failed"
    return instance, "heuristic"


def register_all(classes: Dict[str, Type[BaseExpression]]) -> None:
    for cls in classes.values():
        ExpressionRegistry.register(cls)


def roundtrip_expression(fqn, instance, dialect) -> None:
    """Assert instance round-trips losslessly through all encodings."""
    original_params = instance.get_params()

    for restored in (
        deserialize(serialize(instance), dialect),
        deserialize_json(serialize_json(instance), dialect),
        deserialize_xml(serialize_xml(instance), dialect),
    ):
        _assert_params_equal(restored.get_params(), original_params, fqn)


def sql_consistent(fqn, instance, dialect) -> None:
    """Assert to_sql is identical after round-trip, when the dialect supports it."""
    try:
        expected = instance.to_sql()
    except Exception:
        return
    for restored in (
        deserialize(serialize(instance), dialect),
        deserialize_json(serialize_json(instance), dialect),
        deserialize_xml(serialize_xml(instance), dialect),
    ):
        assert restored.to_sql() == expected, fqn


def _assert_params_equal(a, b, path):
    if isinstance(a, BaseExpression) and isinstance(b, BaseExpression):
        _assert_params_equal(a.get_params(), b.get_params(), path + ".<expr>")
        return
    assert type(a) is type(b) or (
        isinstance(a, (list, tuple, dict)) and isinstance(b, (list, tuple, dict))
    ), f"{path}: type mismatch {type(a).__name__} vs {type(b).__name__}"
    if isinstance(a, dict):
        assert set(a) == set(b), f"{path}: keys differ {set(a) ^ set(b)}"
        for k in a:
            _assert_params_equal(a[k], b[k], f"{path}.{k}")
        return
    if isinstance(a, (list, tuple)):
        assert len(a) == len(b), f"{path}: length differ"
        for i, (x, y) in enumerate(zip(a, b)):
            _assert_params_equal(x, y, f"{path}[{i}]")
        return
    assert a == b, f"{path}: {a!r} != {b!r}"