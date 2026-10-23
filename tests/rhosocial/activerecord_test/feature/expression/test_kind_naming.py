# tests/rhosocial/activerecord_test/feature/expression/test_kind_naming.py
"""Contract tests for the expression registry and the artifact codec.

Three things are enforced here.

The registry is an independent module and starts empty (§7.1)
    It knows no expressions, no core/backend split, no backend names. A fresh
    :class:`ExpressionRegistry` resolves nothing. The framework assembles its
    own instance; the registry never discovers anything itself.

Write and read are asymmetric about the registry (§7.2)
    Serializing must not build or consult one — the node reports its own kind,
    so a caller who only serializes never pays for a registry. Only
    deserializing needs one, and the caller supplies it.

Parameters are matched by name, and ``**kwargs`` is banned
    A catch-all makes a parameter's identity a function of how many extras
    arrived, so it cannot be validated on read and its range cannot be declared
    (§4.8). :func:`decode_artifact` rejects such a class; these tests keep new
    ones from appearing and keep the one existing exception visible.
"""

import ast
import importlib
import inspect
import json
import pkgutil
import subprocess
import sys
import textwrap

import pytest

from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.registry import (
    ExpressionRegistry,
    RegistryError,
    kind_of,
)
from rhosocial.activerecord.backend.expression.serialization import (
    ExpressionDeserializationError,
    deserialize,
    serialize,
)

#: Packages scanned for expression classes: the core tree plus the backends
#: built into this distribution.
_EXPRESSION_PACKAGES = (
    "rhosocial.activerecord.backend.expression",
    "rhosocial.activerecord.backend.impl.sqlite.expression",
    "rhosocial.activerecord.backend.impl.dummy.expression",
)

#: No class may accept ``**kwargs``; the last violation was removed, so there
#: is no allowance list to keep in sync.

#: Classes whose sole parameter is ``*args``-style. Not banned yet; recorded as
#: the baseline a future ban would shrink.
_ALLOWED_BARE_VARIADIC = {
    "AbsoluteFunction", "AbsoluteIntegerFunction", "CeilFunction",
    "CeilIntegerFunction", "CosineFunction", "ExponentialFunction",
    "FloorFunction", "FloorIntegerFunction", "JSONBuildObjectFunction",
    "LogarithmFunction", "ModuloFunction", "PowerFunction", "RoundFunction",
    "RoundIntegerFunction", "SignFunction", "SineFunction",
    "SquareRootFunction", "TangentFunction", "TruncateFunction",
    "TruncateIntegerFunction",
}

#: Stored ``kind``/``KIND``/``kind_name`` fields that disagree with the derived
#: kind. A stored value is a second source of truth (§4.9.2), and a consumer
#: reading it would emit a different kind than the whitelist derives. Nothing
#: is stored any more; the check below keeps it that way.
_KNOWN_KIND_DIVERGENCES = {}


def _iter_expression_classes():
    """Yield every concrete expression class in the framework's packages."""
    seen_modules, seen_classes = set(), set()
    for pkgname in _EXPRESSION_PACKAGES:
        pkg = importlib.import_module(pkgname)
        if hasattr(pkg, "__path__"):
            modnames = [
                m for _, m, _ in pkgutil.walk_packages(
                    path=pkg.__path__, prefix=pkgname + ".", onerror=lambda x: None
                )
            ]
        else:
            modnames = [pkgname]
        for modname in modnames:
            if modname in seen_modules:
                continue
            seen_modules.add(modname)
            try:
                mod = importlib.import_module(modname)
            except Exception:  # pragma: no cover - optional backend modules
                continue
            for name in dir(mod):
                obj = getattr(mod, name, None)
                if not isinstance(obj, type) or obj.__module__ != modname:
                    continue
                if not issubclass(obj, BaseExpression) or obj is BaseExpression:
                    continue
                if getattr(obj, "__abstractmethods__", None):
                    continue  # a base other nodes build on, not a node
                if id(obj) in seen_classes:
                    continue
                seen_classes.add(id(obj))
                yield obj


_ALL = sorted(_iter_expression_classes(), key=lambda c: c.__name__)


def _sqlite_dialect():
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

    return SQLiteDialect()


# ---------------------------------------------------------------------------
# Rule 1: the registry is an independent module that starts empty
# ---------------------------------------------------------------------------


def test_a_fresh_registry_is_empty_and_knows_nothing():
    """§7.1: the registry does not discover, and ships nothing."""
    registry = ExpressionRegistry()
    assert registry.node_kinds() == ()
    with pytest.raises(RegistryError):
        registry.resolve_node("integer_value")
    assert registry.node_kinds() == ()


def test_the_registry_module_does_not_import_expressions():
    """The module must not grow an opinion about what expressions exist."""
    import re

    import rhosocial.activerecord.backend.expression.registry as registry_module

    source = open(registry_module.__file__, encoding="utf-8").read()

    # Match real import statements, not the prose that explains why they are
    # banned — the module's docstring names importlib to say it must not use it.
    assert not re.search(r"^\s*(import\s+importlib|from\s+importlib)", source, re.M), (
        "the registry module imports packages; discovery belongs to the "
        "framework's assembly point, not here"
    )

    # It also holds no backend names: those are the backends' own (§5.1).
    for backend in ("SQLite", "Postgres", "MySQL", "ClickHouse", "BigQuery"):
        assert backend not in source, f"the registry names a backend: {backend}"


def test_framework_default_registry_is_built_on_first_deserialization():
    """The framework assembles one instance; it is not empty once filled."""
    from rhosocial.activerecord.backend.expression import serialization

    registry = serialization.default_registry()
    kinds = registry.node_kinds()
    # The point is "assembled", not a headcount: a number here has to be edited
    # every time a node is added or a class stops being one, and editing it is
    # how the assertion stops meaning anything.
    assert kinds and kinds == tuple(sorted(kinds))
    assert "query_statement" in kinds
    assert "integer_value" in kinds

    # And it is the same instance on every call.
    assert serialization.default_registry() is registry


# ---------------------------------------------------------------------------
# Rule 2: write needs no registry, read does
# ---------------------------------------------------------------------------


def test_serializing_never_builds_a_registry():
    """§7.2: "only json.loads needs it" — a serialize-only caller pays nothing.

    Run in a subprocess so the module global starts genuinely unset; asserting
    this in-process would only prove nothing has deserialized *yet*.
    """
    probe = textwrap.dedent(
        """
        import rhosocial.activerecord.backend.expression.serialization as S
        from rhosocial.activerecord.backend.expression.serialization import serialize
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
        from rhosocial.activerecord.backend.expression import core as C
        from rhosocial.activerecord.backend.expression import query_parts as Q
        from rhosocial.activerecord.backend.expression import predicates as P
        from rhosocial.activerecord.backend.expression.core import Literal
        import rhosocial.activerecord.backend.expression.statements.dql as dql
        d = SQLiteDialect()
        for _ in range(5):
            serialize(dql.QueryStatement(
                d, select=[C.Column(d, "id")], from_=[Q.Table(d, "t")],
                where=Q.WhereClause(d, P.ComparisonPredicate(
                    dialect=d, op=">", left=C.Column(d, "a"), right=Literal(d, 1)))))
            serialize(Literal(d, 1))
        print("BUILT" if S._default_registry is not None else "NOT_BUILT")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True
    )
    assert "NOT_BUILT" in result.stdout, (
        f"serialization built a registry: {result.stdout}{result.stderr[-400:]}"
    )


def test_serialized_node_carries_only_kind_and_params():
    """A bare node: no envelope, and the dialect is absent (§4.11.3)."""
    from rhosocial.activerecord.backend.expression.core import Literal

    dialect = _sqlite_dialect()
    artifact = serialize(Literal(dialect, 42))
    assert list(artifact) == ["kind", "params"]
    assert artifact["kind"] == "integer_value"
    assert artifact["params"]["value"] == 42

    # Nothing that would freeze a dialect or a connection.
    text = json.dumps(artifact)
    for forbidden in ("dialect", "envelope", "version", "connection"):
        assert forbidden not in text


def test_deserialization_takes_the_registry_from_the_caller():
    """An injected registry decides which kinds a read may produce."""
    from rhosocial.activerecord.backend.expression.core import Literal

    dialect = _sqlite_dialect()
    artifact = serialize(Literal(dialect, 42))

    # The caller's own table is authoritative: an empty one accepts nothing.
    # One exception type covers every rejection — unknown kind, or a kind this
    # channel's allowlist withheld — so a reader catches a single thing.
    with pytest.raises(ExpressionDeserializationError) as excinfo:
        deserialize(artifact, dialect, registry=ExpressionRegistry())
    assert "integer_value" in str(excinfo.value)

    # A table holding just that kind reads it back.
    narrow = ExpressionRegistry()
    narrow.register_value_kinds()
    restored = deserialize(artifact, dialect, registry=narrow)
    assert isinstance(restored, Literal)
    assert restored.to_sql() == (Literal(dialect, 42)).to_sql()


def test_kind_whitelist_has_no_collisions():
    """Every kind resolves to exactly one class.

    Two same-named classes derive one kind (§4.11.1), so an artifact could not
    say which it meant. This is the check that caught ``edge_table``.
    """
    by_kind = {}
    for expr_class in _ALL:
        kind = kind_of(expr_class)
        assert by_kind.get(kind, expr_class) is expr_class, (
            f"kind '{kind}' is claimed by both {by_kind[kind].__name__} and "
            f"{expr_class.__name__}"
        )
        by_kind[kind] = expr_class


# ---------------------------------------------------------------------------
# Rule 3: parameters by name; **kwargs banned
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("expr_class", _ALL, ids=lambda c: c.__name__)
def test_constructor_takes_no_kwargs(expr_class):
    """No expression constructor may accept ``**kwargs``.

    There is no allowance list: the last violation (CollateFunction) was
    removed, so any new one is a defect rather than a recorded exception.
    """
    var_keyword = [
        name
        for name, param in inspect.signature(expr_class.__init__).parameters.items()
        if param.kind is inspect.Parameter.VAR_KEYWORD
    ]
    assert not var_keyword, (
        f"{expr_class.__module__}.{expr_class.__name__} accepts "
        f"**{var_keyword[0]}; a catch-all cannot be matched by name on read and "
        f"cannot declare its serialized range (§4.8, §4.11.4)"
    )


def test_the_last_kwargs_violation_was_removed():
    """CollateFunction was the only class with a catch-all; it now round-trips.

    It used to take ``**collation_options``, of which exactly one key was ever
    read (``schema``, for schema-qualified COLLATE). That became a named
    ``schema`` parameter, which is what makes the class serializable at all:
    a catch-all cannot be matched by name on read, so the artifact it produced
    was unreadable.
    """
    collation = importlib.import_module(
        "rhosocial.activerecord.backend.expression.collation"
    )
    core = importlib.import_module("rhosocial.activerecord.backend.expression.core")
    dialect = _sqlite_dialect()
    node = collation.CollateFunction(dialect, core.Column(dialect, "name"), "NOCASE")
    assert not any(
        p.kind is p.VAR_KEYWORD
        for p in inspect.signature(collation.CollateFunction.__init__).parameters.values()
    ), "CollateFunction still accepts **kwargs"
    artifact = serialize(node)
    assert artifact["kind"] == "collate_function"
    restored = deserialize(artifact, dialect)
    assert json.dumps(artifact) == json.dumps(serialize(restored))
    assert node.to_sql()[0] == restored.to_sql()[0]


def test_unregistered_kind_is_refused_explicitly():
    """An artifact naming a kind nobody registered fails, naming the kind."""
    with pytest.raises(ExpressionDeserializationError) as excinfo:
        deserialize({"kind": "no_such_kind", "params": {}}, _sqlite_dialect())
    assert "no_such_kind" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Naming: derived centrally, never stored
# ---------------------------------------------------------------------------


def test_kind_is_a_central_classmethod_no_expression_overrides_it():
    """§4.9.2: the base derives every kind; subclasses supply data, not logic."""
    base_method = BaseExpression.kind.__func__
    overriders = sorted(
        expr_class.__name__
        for expr_class in _ALL
        if "kind" in expr_class.__dict__
        and expr_class.__dict__["kind"].__func__ is not base_method
    )
    assert overriders == [], f"these override kind(): {overriders}"


def test_backend_declares_reserved_tokens_as_data():
    """SQLite owns its compound identifier; the core names no backend."""
    declared = [
        obj for obj in _ALL
        if obj.__module__.startswith("rhosocial.activerecord.backend.impl.sqlite")
        and "SQLite" in obj.__name__
        and obj.KIND_RESERVED == ("SQLite",)
    ]
    assert declared, "no SQLite expression declares KIND_RESERVED"
    for obj in declared:
        assert obj.kind().startswith("sqlite_"), (
            f"{obj.__name__} declares SQLite as reserved but derives "
            f"{obj.kind()!r}"
        )
    assert BaseExpression.KIND_RESERVED == (), "the core must name no backend"


def test_stored_kind_never_contradicts_the_derived_kind():
    drifted = {}
    for expr_class in _ALL:
        for attr in ("kind", "KIND", "kind_name"):
            if attr not in expr_class.__dict__:
                continue
            value = expr_class.__dict__[attr]
            if isinstance(value, str) and value and value != kind_of(expr_class):
                drifted[f"{expr_class.__name__}.{attr}"] = value
    assert drifted == _KNOWN_KIND_DIVERGENCES, (
        "stored kind fields changed — drop fixed entries from "
        f"_KNOWN_KIND_DIVERGENCES: {drifted}"
    )


#: Backend identifier prefixes a kind may carry. A capability several dialects
#: implement is named after the capability (``format_comment_statement``), not
#: after whichever backend's subclass reuses it, so the prefix is optional.
_BACKEND_PREFIXES = (
    "sqlite_", "mysql_", "mariadb_", "postgres_", "oracle_",
    "snowflake_", "clickhouse_", "sqlserver_", "bigquery_", "firebird_",
)


def _declared_format_method(cls):
    """The literal this class's own ``format_method`` yields, or ``None``."""
    try:
        source = textwrap.dedent(inspect.getsource(cls))
    except (OSError, TypeError):
        return None
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef) and node.name == "format_method":
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant):
                    return stmt.value.value
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "format_method":
                    if isinstance(node.value, ast.Constant):
                        return node.value.value
    return None


def test_every_declared_formatter_names_its_kind():
    """§3: a statement/expression node's formatter is ``format_`` plus its kind.

    The backend prefix may be dropped, but no other word may be added, removed
    or respelled — that is what keeps the class name, the kind and the dialect
    method from drifting apart.

    Scoped to ``*Statement`` / ``*Expression``. The object-reference family
    (``Table``, ``IntegerColumn``, ``Literal``, ...) deliberately shares one
    renderer across several kinds — ``format_column`` serves ten column types —
    so those method names describe the capability, not the kind.
    """
    offenders = []
    for expr_class in _ALL:
        if not expr_class.__name__.endswith(("Statement", "Expression")):
            continue
        method = _declared_format_method(expr_class)
        if method is None:
            continue
        kind = expr_class.kind()
        allowed = {"format_" + kind}
        for prefix in _BACKEND_PREFIXES:
            if kind.startswith(prefix):
                allowed.add("format_" + kind[len(prefix):])
        if method not in allowed:
            offenders.append(f"{expr_class.__name__}: {method} (kind {kind})")
    assert offenders == [], (
        "formatter names that do not name their kind: " + repr(offenders)
    )


def test_expression_packages_were_actually_scanned():
    """Guard the guard: an empty scan makes every rule above vacuous."""
    assert len(_ALL) > 300, f"only found {len(_ALL)} expression classes"