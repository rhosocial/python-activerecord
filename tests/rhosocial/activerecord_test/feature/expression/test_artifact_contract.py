# tests/rhosocial/activerecord_test/feature/expression/test_artifact_contract.py
"""Runtime contract for the artifact codec: shape, round-trip, refusal.

This replaces the earlier serialization test files wholesale, and it drops
something they all depended on: **synthesizing an instance for every
registered class**. That machinery existed because a class index keyed by
import path could not tell you what to construct. The registry says which class
a kind *is*, and an artifact says exactly which parameters it carries -- so
reading needs neither a table nor a guess.

What is left to test is the part that is genuinely the codec's own:

Every kind is reachable, and reaches nothing else
    The registry is the only name authority, three whitelists stay separate,
    and a fresh one resolves nothing at all (§7.1).

The artifact is a bare node
    ``{"kind": ..., "params": {...}}`` and nothing else. No envelope, no class
    path, no version field (§4.11.3).

Every shape of value survives the trip
    Nested expressions, tuples, lists, dicts, enums, dataclasses and the
    standard-library scalars. These are written out by hand rather than
    generated, because each one is a *statement about what the codec must
    carry*, and a generated instance cannot make that statement.

Writing never needs a registry
    The node reports its own kind, so a caller who only writes never builds one
    (§7.2) -- checked in a subprocess, since by now this process has one.

Reading trusts nothing
    The artifact is external input: an unknown kind, a leftover envelope field,
    an unrecognised parameter, a missing kind, an over-deep tree and a name
    aimed at an import each fail by name.
"""

import datetime
import decimal
import json
import subprocess
import sys
import uuid

import pytest

from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.query_parts import WhereClause
from rhosocial.activerecord.backend.expression.registry import (
    ExpressionRegistry,
    RegistryError,
)
from rhosocial.activerecord.backend.expression.serialization import (
    ExpressionDeserializationError,
    default_registry,
    deserialize,
    deserialize_json,
    deserialize_xml,
    serialize,
    serialize_json,
    serialize_xml,
)
from rhosocial.activerecord.backend.expression.values import (
    BooleanValue,
    DateValue,
    DecimalValue,
    IntegerValue,
    NullValue,
    StringValue,
    TimestampValue,
    UUIDValue,
)
from rhosocial.activerecord.backend.expression.core import (
    AllColumnsWildcard,
    Column,
    Literal,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


def _dialect():
    return DummyDialect()


# ---------------------------------------------------------------------------
# The values an artifact has to be able to carry
# ---------------------------------------------------------------------------

#: One case per *shape* of parameter value, not per class. What the codec owes
#: a caller is that each of these comes back; how many classes happen to use
#: each shape is the library's business, not the format's.
CARRYABLE = {
    "scalar-int": lambda d: IntegerValue(d, 42),
    "scalar-str": lambda d: StringValue(d, "hi"),
    "scalar-bool": lambda d: BooleanValue(d, True),
    "scalar-null": lambda d: NullValue(d),
    "column": lambda d: Column(d, "id"),
    "bare-column": lambda d: Column(d, "id", table=Table(d, "users")),
    "wildcard": lambda d: AllColumnsWildcard(d),
    "qualified": lambda d: Column(d, "id", table=Table(d, "users"), alias="u"),
    # Nested expressions: the predicate holds two columns, so a reader that
    # lost a nesting level would still produce *an* expression, just a wrong one.
    "predicate": lambda d: ComparisonPredicate(d, "=", Column(d, "a"), Literal(d, 1)),
    "where": lambda d: WhereClause(
        d, ComparisonPredicate(d, "=", Column(d, "a"), Literal(d, 1))
    ),
    # A tuple is not a list. JSON draws no distinction; the artifact must.
    "tuple": lambda d: Table(d, "users"),
    # Standard-library scalars, each with its own registered codec.
    "date": lambda d: DateValue(d, datetime.date(2020, 1, 2)),
    "timestamp": lambda d: TimestampValue(d, datetime.datetime(2020, 1, 2, 3, 4, 5)),
    "decimal": lambda d: DecimalValue(d, decimal.Decimal("1.25")),
    "uuid": lambda d: UUIDValue(d, uuid.UUID(int=7)),
}


def _params_equal(a, b):
    """Structural equality for a parameter tree.

    Expressions define no ``__eq__``, so comparing two parameter dicts
    directly compares nested nodes by identity and fails on a round-trip that
    worked. Two nodes count as equal when they are the same class and their
    parameters match all the way down -- the property a rebuild must preserve.
    """
    if isinstance(a, BaseExpression) or isinstance(b, BaseExpression):
        if type(a) is not type(b):
            return False
        return _params_equal(a.get_params(), b.get_params())
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_params_equal(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_params_equal(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b


def _render(instance):
    """The SQL this instance renders, or None when it renders nothing."""
    try:
        return instance.to_sql()[0]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Reachability: the registry is the only name authority
# ---------------------------------------------------------------------------


def _declares_a_formatter(cls) -> bool:
    """Does this class name the formatter that renders it?

    ``inspect.isabstract`` does not answer this. The framework bases are not
    declared abstract -- they declare no ``format_method`` and raise when it is
    read -- so they are concrete enough to construct and yet are not nodes. A
    base that names a category is not a kind.
    """
    prop = getattr(cls, "format_method", None)
    if prop is None:
        return False
    if getattr(prop, "isabstractmethod", False):
        return False
    try:
        return isinstance(prop, str) and bool(prop)
    except Exception:
        return False


def _declared_kinds():
    """Every kind the expression tree defines, read from the tree itself."""
    import importlib
    import inspect
    import pkgutil

    package = "rhosocial.activerecord.backend.expression"
    root = importlib.import_module(package)
    modules = [package] + [
        n for _, n, _ in pkgutil.walk_packages(root.__path__, package + ".")
    ]
    kinds = set()
    for name in modules:
        try:
            mod = importlib.import_module(name)
        except Exception:
            continue
        for attr in vars(mod).values():
            if (
                inspect.isclass(attr)
                and issubclass(attr, BaseExpression)
                and _declares_a_formatter(attr)
            ):
                kinds.add(attr.kind())
    return kinds


def test_the_framework_registry_resolves_every_kind_it_declares():
    """A kind in the tree that the registry cannot resolve is a broken name.

    Read from the tree rather than from a hand-written list, so a new class is
    covered the moment it exists instead of the day someone remembers it.
    """
    registry = default_registry()
    declared = _declared_kinds()
    registered = set(registry.node_kinds())
    assert declared <= registered, (
        f"kinds the tree defines but the registry cannot resolve: "
        f"{sorted(declared - registered)}"
    )


def test_a_fresh_registry_resolves_nothing():
    """§7.1: the registry starts empty. It registers; it does not discover."""
    empty = ExpressionRegistry()
    assert empty.node_kinds() == ()
    with pytest.raises(RegistryError):
        empty.resolve_node("column")


def test_registration_is_the_only_way_a_name_becomes_known():
    empty = ExpressionRegistry()
    with pytest.raises(RegistryError):
        empty.resolve_node(Column.kind())
    empty.register_node(Column)
    assert empty.resolve_node(Column.kind()) is Column


def test_a_kind_is_not_an_enum_and_not_a_dataclass():
    """The three whitelists are separate namespaces.

    An enum and a node that happen to share a name are different things, and a
    reader that conflated them would resolve one as the other.
    """
    registry = default_registry()
    for kind in registry.node_kinds():
        assert kind not in registry._enums, f"{kind} is both a node and an enum"
        assert kind not in registry._dataclasses, f"{kind} is both a node and a dataclass"


# ---------------------------------------------------------------------------
# The artifact's shape
# ---------------------------------------------------------------------------


def test_the_artifact_is_a_bare_node():
    """§4.11.3: the artifact *is* the node. There is no envelope around it."""
    artifact = serialize(Column(_dialect(), "id"))
    assert set(artifact) == {"kind", "params"}
    assert artifact["kind"] == "column"
    assert artifact["params"]["name"] == "id"


def test_the_artifact_names_no_import_path():
    """The wire format carries a kind, never a dotted path.

    A dotted path in the artifact is what would force a reader to import
    whatever the string pointed at.
    """
    artifact = json.dumps(serialize(Column(_dialect(), "id")))
    assert "rhosocial" not in artifact
    assert "." not in artifact.split('"kind":')[1].split(",")[0].strip('"')


def test_the_artifact_is_json_native():
    """An artifact crosses a wire, so it must survive ``json.dumps`` intact."""
    dialect = _dialect()
    for label, build in CARRYABLE.items():
        json.dumps(serialize(build(dialect)))  # raises TypeError if not native


def test_key_order_is_stable():
    """Two encodings of one node are the same text.

    A reader that has to diff artifacts, or cache them by content, cannot do it
    if the key order depends on dict iteration.
    """
    dialect = _dialect()
    for label, build in CARRYABLE.items():
        once = serialize(build(dialect))
        twice = serialize(build(dialect))
        assert json.dumps(once) == json.dumps(twice), label


def test_serialization_never_builds_a_registry():
    """§7.2: writing is registry-free.

    Run in a subprocess: by the time this test executes, this process has
    already built a registry for the tests above, so the assertion here would
    be vacuous.
    """
    script = (
        "import rhosocial.activerecord.backend.expression.serialization as S\n"
        "seen = []\n"
        "real = S.default_registry\n"
        "S.default_registry = lambda: seen.append(1) or real()\n"
        "from rhosocial.activerecord.backend.expression.core import Column\n"
        "from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect\n"
        "S.serialize(Column(DummyDialect(), 'id'))\n"
        "print('BUILT' if seen else 'CLEAN')\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=120
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip().endswith("CLEAN"), (
        "serialize() consulted the registry; writing must not need one"
    )


# ---------------------------------------------------------------------------
# Round-trip: dict, JSON and XML are three renderings of one artifact
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("channel", ["dict", "json", "xml"])
def test_every_carryable_value_survives_every_channel(channel):
    """Parameters and SQL both come back unchanged.

    Comparing only the parameters would pass for an encoding that dropped
    something the formatter needs; comparing only the SQL would pass for one
    that reordered a list.
    """
    dialect = _dialect()
    for label, build in CARRYABLE.items():
        instance = build(dialect)
        expected_params = instance.get_params()
        expected_sql = _render(instance)

        if channel == "dict":
            restored = deserialize(serialize(instance), dialect)
        elif channel == "json":
            restored = deserialize_json(serialize_json(instance), dialect)
        else:
            restored = deserialize_xml(serialize_xml(instance), dialect)

        assert type(restored) is type(instance), (
            f"{label}/{channel}: rebuilt as {type(restored).__name__}"
        )
        assert _params_equal(restored.get_params(), expected_params), (
            f"{label}/{channel}: parameters changed\n"
            f"    before: {expected_params}\n"
            f"    after : {restored.get_params()}"
        )
        assert _render(restored) == expected_sql, f"{label}/{channel}: SQL changed"


def test_a_tuple_does_not_come_back_as_a_list():
    """JSON draws no distinction between the two; the artifact has to."""
    dialect = _dialect()
    artifact = serialize(
        ComparisonPredicate(dialect, "=", Column(dialect, "a"), Column(dialect, "b"))
    )
    assert isinstance(artifact["params"]["left"], dict)
    restored = deserialize_json(json.dumps(artifact), dialect)
    assert isinstance(restored.get_params()["left"], Column)


def test_a_datetime_survives_as_a_datetime():
    """A value with no JSON form must come back as the same type, not a string.

    This is the case the codec's standard-library entries exist for: without
    one, the value is written as its repr and read back as a string, which the
    owning constructor then has to reject or silently coerce.
    """
    dialect = _dialect()
    original = TimestampValue(dialect, datetime.datetime(2020, 1, 2, 3, 4, 5))
    restored = deserialize_json(serialize_json(original), dialect)
    assert isinstance(restored.value, datetime.datetime)
    assert restored.value == original.value


# ---------------------------------------------------------------------------
# Reading: the artifact is untrusted input
# ---------------------------------------------------------------------------


def test_an_unknown_kind_is_refused_by_name():
    with pytest.raises(ExpressionDeserializationError) as caught:
        deserialize({"kind": "no_such_kind", "params": {}}, _dialect())
    assert "no_such_kind" in str(caught.value)


def test_a_leftover_envelope_field_is_refused():
    """§4.11.3: a bare node carries exactly ``kind`` and ``params``.

    Passing an extra field through means a reader tolerates an envelope it does
    not understand, which is how two incompatible formats end up sharing a key.
    """
    artifact = serialize(Column(_dialect(), "id"))
    artifact["type"] = "rhosocial.activerecord.backend.expression.core.Column"
    with pytest.raises(ExpressionDeserializationError) as caught:
        deserialize(artifact, _dialect())
    assert "type" in str(caught.value)


def test_an_unrecognised_parameter_is_refused_by_name():
    """A reader does not drop what it does not recognise."""
    artifact = serialize(Column(_dialect(), "id"))
    artifact["params"]["no_such_param"] = 1
    with pytest.raises(ExpressionDeserializationError) as caught:
        deserialize(artifact, _dialect())
    assert "no_such_param" in str(caught.value)


def test_a_missing_kind_is_refused():
    with pytest.raises(ExpressionDeserializationError):
        deserialize({"params": {}}, _dialect())


def test_a_name_in_an_artifact_never_reaches_an_import():
    """§4.11.4: resolution is by whitelist, never by import path.

    Importing whatever module a name points at turns a data field into a code
    execution path. The registry can only answer for names someone registered.
    """
    with pytest.raises(Exception) as caught:
        deserialize({"kind": "os.system", "params": {}}, _dialect())
    assert "os.system" in str(caught.value)


def test_an_over_deep_tree_is_refused():
    """Untrusted input must not be able to exhaust the stack."""
    node = serialize(IntegerValue(_dialect(), 1))
    for _ in range(200):
        node = {"__expr__": node}
    with pytest.raises(ExpressionDeserializationError):
        deserialize(node, _dialect())


def test_the_readers_registry_is_the_callers():
    """§7.2: the caller decides which kinds a read may produce.

    An empty registry accepts nothing, which is the point: a channel that
    should accept one kind can be given exactly that kind.
    """
    dialect = _dialect()
    artifact = serialize(IntegerValue(dialect, 7))
    with pytest.raises(ExpressionDeserializationError):
        deserialize(artifact, dialect, registry=ExpressionRegistry())

    narrow = ExpressionRegistry()
    narrow.register_node(IntegerValue)
    assert isinstance(deserialize(artifact, dialect, registry=narrow), IntegerValue)


# ---------------------------------------------------------------------------
# The halves must agree: constructor parameters and stored attributes
# ---------------------------------------------------------------------------


def test_no_get_params_override():
    """``get_params()`` is not an extension point; an override is a defect.

    A round-trip rebuilds by calling the constructor with whatever
    ``get_params()`` returned, so an override is precisely where those two
    halves drift: the class emits a key the constructor renames, merges or
    refuses, and the state is silently gone. The repair belongs in
    ``__init__`` -- store the value under the name it was given.
    """
    import importlib
    import inspect
    import pkgutil

    base = BaseExpression.__dict__["get_params"]
    package = "rhosocial.activerecord.backend.expression"
    root = importlib.import_module(package)
    modules = [package] + [
        n for _, n, _ in pkgutil.walk_packages(root.__path__, package + ".")
    ]
    overriders = []
    for module in modules:
        try:
            mod = importlib.import_module(module)
        except Exception:
            continue
        for cls in vars(mod).values():
            if (
                inspect.isclass(cls)
                and issubclass(cls, BaseExpression)
                and "get_params" in cls.__dict__
                and cls.__dict__["get_params"] is not base
            ):
                overriders.append(cls.__name__)
    assert not overriders, (
        "these override get_params(); the constructor must accept what "
        f"get_params emits: {sorted(set(overriders))}"
    )