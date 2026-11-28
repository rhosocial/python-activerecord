# tests/rhosocial/activerecord_test/feature/expression/test_expression_registry.py
"""The registry namespace is independent, and its tables are kind -> FQN data.

The expression definitions and the registration tables are two namespaces:

* ``backend.expression`` declares nodes and nothing else;
* ``backend.expression_registry`` owns the table type, the collection of kinds,
  core's mapping/table, and the codec;
* a dialect only renders.

A backend's table is a dictionary merge: core's mapping plus its own. There is
no generic assembly step to name.
"""

import ast
import importlib
import inspect
import datetime
import decimal
import uuid
from pathlib import Path

import pytest

from rhosocial.activerecord.backend import expression as expression_package
from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.expression.column_types.column import Column
from rhosocial.activerecord.backend.expression.functions.function_call import FunctionCall
from rhosocial.activerecord.backend.expression.value_types.parameter import Parameter
from rhosocial.activerecord.backend.expression.operators.operators import RawSQL
from rhosocial.activerecord.backend.expression.predicates.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression_registry import (
    ArtifactError,
    CORE_EXPRESSIONS,
    CORE_EXPRESSION_REGISTRY,
    ExpressionDeserializationError,
    ExpressionRegistry,
    ExpressionSerializer,
    RegistryError,
    collect_expressions,
    deserialize,
    deserialize_json,
    deserialize_xml,
    merge_expressions,
    serialize,
    serialize_json,
    serialize_xml,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.dummy.expression_registry import (
    DUMMY_EXPRESSIONS,
    DUMMY_EXPRESSION_REGISTRY,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression.statements.vacuum import (
    SQLiteVacuumStatement,
)
from rhosocial.activerecord.backend.impl.sqlite.expression_registry import (
    SQLITE_EXPRESSIONS,
    SQLITE_EXPRESSION_REGISTRY,
)

_REGISTRY_NAMES = (
    "CORE_EXPRESSION_REGISTRY",
    "CORE_EXPRESSIONS",
    "ExpressionRegistry",
    "serialize",
    "deserialize",
)


def _sqlite() -> SQLiteDialect:
    return SQLiteDialect((3, 38, 0))


def _backend_package_dir() -> Path:
    package = importlib.import_module("rhosocial.activerecord.backend")
    for candidate in vars(package).get("__path__", ()):
        path = Path(candidate).resolve()
        if path.is_dir():
            return path
    raise AssertionError("the installed backend package exposes no directory")


def _imported_modules(path: Path):
    """Every module a Python file imports, absolute and relative alike."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def _global_statements(path: Path):
    """Line numbers of ``global`` statements in uncommented code."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Global)]


# ---------------------------------------------------------------------------
# The split is a namespace boundary, not a naming convention
# ---------------------------------------------------------------------------


def test_expression_package_exports_definitions_and_no_registration():
    """``backend.expression`` does not re-export a table or the codec."""
    for name in _REGISTRY_NAMES:
        assert not hasattr(expression_package, name), (
            f"backend.expression exposes {name}; registration belongs to "
            f"backend.expression_registry"
        )
        assert name not in expression_package.__all__


def test_expression_never_imports_the_registry_namespace():
    """The dependency runs one way: registration reads definitions, not the reverse."""
    root = _backend_package_dir() / "expression"
    offenders = [
        f"{path.relative_to(root)}:{module}"
        for path in root.rglob("*.py")
        for module in _imported_modules(path)
        if "expression_registry" in module
    ]
    assert offenders == [], "expression modules import the registry namespace: " + repr(
        offenders
    )


def test_dialects_never_import_the_registry_namespace():
    """A dialect renders; it neither owns a table nor selects one."""
    root = _backend_package_dir()
    offenders = [
        f"{path.relative_to(root)}:{module}"
        for path in root.rglob("*.py")
        if path.name == "dialect.py" or "dialect" in path.parts
        for module in _imported_modules(path)
        if "expression_registry" in module
    ]
    assert offenders == [], "dialects import the registry namespace: " + repr(offenders)


def test_registry_namespace_imports_no_implementation_or_dialect():
    """The mechanism is independent of the backends and the dialects."""
    root = _backend_package_dir() / "expression_registry"
    offenders = [
        f"{path.relative_to(root)}:{module}"
        for path in root.rglob("*.py")
        for module in _imported_modules(path)
        if module.split(".")[-1] in {"impl", "dialect"} or module.startswith("impl.")
    ]
    assert offenders == [], "the registry namespace reaches into an owner: " + repr(
        offenders
    )


def test_the_registry_namespace_has_no_global_statement():
    """A cache is a value, not a rebindable process global."""
    root = _backend_package_dir() / "expression_registry"
    offenders = [
        f"{path.relative_to(root)}:{lines}"
        for path in root.rglob("*.py")
        for lines in [_global_statements(path)]
        if lines
    ]
    assert offenders == [], "global statements in the registry namespace: " + repr(
        offenders
    )


def test_there_is_no_generic_package_assembler_to_call():
    """Owners merge mappings; there is no walker with a ``base=`` parameter."""
    package = importlib.import_module("rhosocial.activerecord.backend.expression_registry")
    assert not hasattr(package, "registry_for_packages")


# ---------------------------------------------------------------------------
# One table per owner, and no dialect among the owners
# ---------------------------------------------------------------------------


def test_a_fresh_registry_is_empty_and_refuses_mutation_once_frozen():
    registry = ExpressionRegistry()
    assert registry.node_kinds() == ()
    assert not registry.is_frozen

    frozen = ExpressionRegistry().freeze()
    with pytest.raises(Exception) as caught:
        frozen.register_node(Column)
    assert "frozen" in str(caught.value)


def test_core_expressions_is_kind_to_fqn_data_without_backend_kinds():
    """``CORE_EXPRESSIONS`` names classes; it does not import them to build."""
    assert isinstance(CORE_EXPRESSIONS, dict)
    target = CORE_EXPRESSIONS["column"]
    assert target == f"{Column.__module__}.{Column.__qualname__}"
    assert CORE_EXPRESSIONS["parameter"].endswith(".Parameter")

    assert "query_statement" in CORE_EXPRESSIONS
    kinds = set(CORE_EXPRESSIONS)
    assert not [kind for kind in kinds if kind.startswith("sqlite_")]
    assert not [kind for kind in kinds if kind.startswith("_dummy")]


def test_core_registry_resolves_registered_fqns_and_stays_frozen():
    registry = CORE_EXPRESSION_REGISTRY
    assert registry.is_frozen
    assert registry.node_kinds() == tuple(sorted(CORE_EXPRESSIONS))
    assert registry.resolve_node("column") is Column
    assert registry.resolve_node("parameter") is Parameter

    with pytest.raises(Exception) as caught:
        registry.resolve_node("sqlite_vacuum_statement")
    assert "sqlite_vacuum_statement" in str(caught.value)


def test_a_registry_can_be_built_from_a_plain_mapping():
    target = f"{Column.__module__}.{Column.__qualname__}"
    registry = ExpressionRegistry({"column": target}).freeze()
    assert registry.node_kinds() == ("column",)
    assert registry.resolve_node("column") is Column


def test_a_backend_table_is_the_merge_of_core_and_its_own():
    assert "sqlite_vacuum_statement" in SQLITE_EXPRESSIONS
    assert SQLITE_EXPRESSIONS["sqlite_vacuum_statement"].endswith(
        ".SQLiteVacuumStatement"
    )
    assert "_dummy_type_definition" in DUMMY_EXPRESSIONS

    sqlite_kinds = set(SQLITE_EXPRESSION_REGISTRY.node_kinds())
    dummy_kinds = set(DUMMY_EXPRESSION_REGISTRY.node_kinds())
    assert sqlite_kinds == set(CORE_EXPRESSIONS) | set(SQLITE_EXPRESSIONS)
    assert dummy_kinds == set(CORE_EXPRESSIONS) | set(DUMMY_EXPRESSIONS)

    assert "sqlite_vacuum_statement" not in dummy_kinds
    assert "_dummy_type_definition" not in sqlite_kinds
    assert SQLITE_EXPRESSION_REGISTRY.resolve_node("column") is Column
    assert SQLITE_EXPRESSION_REGISTRY.is_frozen
    assert DUMMY_EXPRESSION_REGISTRY.is_frozen


def test_dialects_carry_no_registry():
    """Being able to render a kind is not the same as owning the read table."""
    assert not hasattr(SQLDialectBase(), "artifact_registry")
    assert not hasattr(SQLiteDialect(), "artifact_registry")
    assert not hasattr(DummyDialect(), "artifact_registry")

    class PlainDialect(SQLDialectBase):
        pass

    assert not hasattr(PlainDialect(), "artifact_registry")


# ---------------------------------------------------------------------------
# The codec: writing needs no table; reading names one
# ---------------------------------------------------------------------------


def test_a_core_artifact_round_trips_and_renders_through_a_dialect():
    artifact = serialize(Column(None, "id"))
    assert list(artifact) == ["kind", "params"]

    restored = deserialize(artifact)
    assert isinstance(restored, Column)
    assert restored.to_sql(_sqlite()) == ('"id"', ())
    assert isinstance(deserialize_json(serialize_json(Column(None, "id"))), Column)
    assert isinstance(deserialize_xml(serialize_xml(Column(None, "id"))), Column)


def test_a_backend_kind_needs_its_table_explicitly():
    """A dialect does not widen a read; the caller's table does."""
    sqlite = _sqlite()
    artifact = serialize(SQLiteVacuumStatement(sqlite))

    with pytest.raises(ExpressionDeserializationError) as caught:
        deserialize(artifact)
    assert "sqlite_vacuum_statement" in str(caught.value)

    restored = deserialize(artifact, registry=SQLITE_EXPRESSION_REGISTRY)
    assert isinstance(restored, SQLiteVacuumStatement)
    assert restored.to_sql(sqlite) == ("VACUUM", ())

    assert isinstance(
        deserialize_json(
            serialize_json(SQLiteVacuumStatement(sqlite)),
            registry=SQLITE_EXPRESSION_REGISTRY,
        ),
        SQLiteVacuumStatement,
    )
    assert isinstance(
        deserialize_xml(
            serialize_xml(SQLiteVacuumStatement(sqlite)),
            registry=SQLITE_EXPRESSION_REGISTRY,
        ),
        SQLiteVacuumStatement,
    )


def test_a_narrowed_table_refuses_a_kind_it_does_not_hold():
    artifact = serialize(SQLiteVacuumStatement(_sqlite()))
    narrowed = CORE_EXPRESSION_REGISTRY.twin()
    with pytest.raises(ExpressionDeserializationError) as caught:
        deserialize(artifact, registry=narrowed)
    assert "sqlite_vacuum_statement" in str(caught.value)


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        18,
        1.5,
        "abc",
        datetime.date(2020, 1, 2),
        decimal.Decimal("1.25"),
        b"\x00\x01",
        uuid.UUID("00000000-0000-0000-0000-000000000001"),
    ],
)
def test_a_parameter_value_is_carried_as_is(value):
    """No type field, no conversion: the artifact carries the host value."""
    artifact = serialize(Parameter(None, value))
    assert artifact == {"kind": "parameter", "params": {"value": value, "inline": False}}
    assert deserialize(artifact).value == value


def test_a_parameter_round_trips_through_json_when_json_can_write_it():
    for value in (None, True, 18, 1.5, "abc"):
        restored = deserialize_json(serialize_json(Parameter(None, value)))
        assert restored.value == value
        assert deserialize_xml(serialize_xml(Parameter(None, value))).value == value


def test_containers_keep_their_json_shape():
    """A tuple travels as an array; the reader cannot infer the host type."""
    artifact = serialize(Parameter(None, (1, 2)))
    assert artifact["params"]["value"] == [1, 2]
    assert deserialize(artifact).value == [1, 2]


def test_an_unknown_kind_and_a_leftover_field_are_refused_by_name():
    with pytest.raises(ExpressionDeserializationError) as caught:
        deserialize({"kind": "no_such_kind", "params": {}})
    assert "no_such_kind" in str(caught.value)

    artifact = serialize(Column(None, "id"))
    artifact["type"] = "an envelope field"
    with pytest.raises(ExpressionDeserializationError) as caught:
        deserialize(artifact)
    assert "type" in str(caught.value)


def test_a_channel_allowlist_narrows_a_table_without_widening_it():
    serializer = ExpressionSerializer(allowed_types=["column"])
    assert isinstance(serializer.deserialize(serialize(Column(None, "id"))), Column)
    with pytest.raises(ExpressionDeserializationError) as caught:
        serializer.deserialize(serialize(Parameter(None, 1)))
    assert "parameter" in str(caught.value)


def test_caller_vouched_sql_needs_an_explicit_registration():
    assert RawSQL.REGISTER_BY_DEFAULT is False
    assert "raw_sql" not in CORE_EXPRESSION_REGISTRY.node_kinds()

    artifact = serialize(RawSQL(None, "SELECT 1"))
    with pytest.raises(ExpressionDeserializationError) as caught:
        deserialize(artifact)
    assert "raw_sql" in str(caught.value)

    trusted = CORE_EXPRESSION_REGISTRY.twin()
    trusted.register_node(RawSQL)
    restored = deserialize(artifact, registry=trusted)
    assert isinstance(restored, RawSQL)
    assert restored.expression == "SELECT 1"


def test_deserialize_does_not_take_a_dialect():
    """The signature states the rule: rendering is separate from reading."""
    for function in (deserialize, deserialize_json, deserialize_xml):
        parameters = set(inspect.signature(function).parameters)
        assert "dialect" not in parameters, (
            f"{function.__name__} still takes a dialect: {sorted(parameters)}"
        )

def test_merge_refuses_a_kind_two_targets_claim():
    with pytest.raises(ValueError) as caught:
        merge_expressions({"column": "a.B"}, {"column": "c.D"})
    assert "column" in str(caught.value)

    fused = merge_expressions({"column": "a.B"}, {"column": "a.B"})
    assert fused == {"column": "a.B"}


def test_collect_skips_a_package_that_is_not_installed():
    assert collect_expressions("no.such.package") == {}


def test_registry_mutation_and_disable_are_explicit():
    registry = ExpressionRegistry({"column": f"{Column.__module__}.{Column.__qualname__}"})
    assert registry.is_enabled("column")
    registry.disable("column")
    assert not registry.is_enabled("column")
    with pytest.raises(Exception) as caught:
        registry.resolve_node("column")
    assert "disabled" in str(caught.value)
    registry.enable("column")
    assert registry.resolve_node("column") is Column

    registry.unregister_node("column")
    assert registry.node_kinds() == ()
    with pytest.raises(RegistryError):
        registry.unregister_node("column")


def test_resolve_reports_a_target_that_cannot_be_imported():
    registry = ExpressionRegistry({"column": "no.such.module.Column"})
    with pytest.raises(Exception) as caught:
        registry.resolve_node("column")
    assert "no.such.module" in str(caught.value)


def test_serializer_max_depth_applies_to_both_directions():
    expr = Parameter(None, 1)
    for _ in range(6):
        expr = FunctionCall(None, "f", expr)

    with pytest.raises(ArtifactError):
        ExpressionSerializer(max_depth=3).serialize(expr)

    artifact = serialize(expr)
    with pytest.raises(ExpressionDeserializationError):
        ExpressionSerializer(max_depth=3).deserialize(artifact)


def test_a_nested_parameter_is_an_ordinary_node():
    expr = ComparisonPredicate(None, ">", Column(None, "age"), 18)
    artifact = serialize(expr)
    assert artifact["params"]["right"] == {
        "kind": "parameter",
        "params": {"value": 18, "inline": False},
    }
    restored = deserialize(artifact)
    assert isinstance(restored, ComparisonPredicate)
    assert isinstance(restored.right, Parameter)
    assert restored.right.value == 18


def test_inline_is_carried_by_the_literal_artifact():
    artifact = serialize(Parameter(None, 1, inline=True))
    assert artifact["params"]["inline"] is True
    restored = deserialize(artifact)
    assert isinstance(restored, Parameter)
    assert restored.inline is True


def test_unknown_and_missing_parameters_are_refused_by_name():
    artifact = serialize(Column(None, "id"))
    artifact["params"]["bogus"] = 1
    with pytest.raises(ExpressionDeserializationError) as caught:
        deserialize(artifact)
    assert "bogus" in str(caught.value)

    with pytest.raises(ExpressionDeserializationError) as caught:
        deserialize({"kind": "parameter", "params": {"inline": False}})
    assert "value" in str(caught.value)

def test_merged_is_a_frozen_union_and_leaves_the_inputs_alone():
    first = ExpressionRegistry({"column": f"{Column.__module__}.{Column.__qualname__}"})
    second = ExpressionRegistry({"parameter": f"{Parameter.__module__}.{Parameter.__qualname__}"})
    fused = first.merged(second)
    assert fused.is_frozen
    assert set(fused.node_kinds()) == {"column", "parameter"}
    assert first.node_kinds() == ("column",)
    assert second.node_kinds() == ("parameter",)

    with pytest.raises(RegistryError) as caught:
        first.merged(ExpressionRegistry({"column": "a.B"}))
    assert "column" in str(caught.value)


def test_registering_the_same_target_twice_is_a_noop_and_two_targets_collide():
    registry = ExpressionRegistry()
    assert registry.register_node(Column) == "column"
    assert registry.register_node(Column) == "column"
    assert registry.node_kinds() == ("column",)

    Alien = type("Column", (Column,), {"__module__": "tests.alien"})
    with pytest.raises(RegistryError) as caught:
        registry.register_node(Alien)
    assert "column" in str(caught.value)


def test_merged_requires_a_registry():
    with pytest.raises(TypeError):
        ExpressionRegistry().merged({"column": "a.B"})


def test_non_object_params_are_refused():
    with pytest.raises(ExpressionDeserializationError) as caught:
        deserialize({"kind": "column", "params": []})
    assert "params" in str(caught.value)


def test_a_predicate_with_a_nested_literal_round_trips_through_xml():
    expr = ComparisonPredicate(None, ">", Column(None, "age"), Parameter(None, 18))
    payload = serialize_xml(expr)
    restored = deserialize_xml(payload)
    assert isinstance(restored, ComparisonPredicate)
    assert isinstance(restored.right, Parameter)
    assert restored.right.value == 18

def test_a_missing_required_parameter_is_refused():
    with pytest.raises(ExpressionDeserializationError) as caught:
        deserialize({"kind": "column", "params": {}})
    assert "missing required" in str(caught.value)

def test_a_custom_value_type_uses_the_callers_json_hooks():
    """The serializer passes default/object_hook straight to the json module."""

    class Money:
        def __init__(self, amount):
            self.amount = amount

    def encode(obj):
        if isinstance(obj, Money):
            return {"__money__": obj.amount}
        raise TypeError(f"cannot encode {type(obj).__name__}")

    def decode(obj):
        if set(obj) == {"__money__"}:
            return Money(obj["__money__"])
        return obj

    parameter = Parameter(None, Money(5))
    with pytest.raises(TypeError):
        serialize_json(parameter)

    text = serialize_json(parameter, default=encode)
    restored = deserialize_json(text, object_hook=decode)
    assert isinstance(restored, Parameter)
    assert isinstance(restored.value, Money)
    assert restored.value.amount == 5

