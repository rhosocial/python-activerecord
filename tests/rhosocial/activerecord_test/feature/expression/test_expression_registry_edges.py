# tests/rhosocial/activerecord_test/feature/expression/test_expression_registry_edges.py
"""Edge branches of the registry and the codec that the main tests do not reach."""

import pytest

from rhosocial.activerecord.backend.expression.core import Column, FunctionCall, Parameter
from rhosocial.activerecord.backend.expression_registry import (
    ArtifactError,
    ExpressionRegistry,
    ExpressionSerializer,
    RegistryError,
    deserialize,
    deserialize_xml,
    serialize,
    serialize_xml,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


def _dialect() -> SQLiteDialect:
    return SQLiteDialect((3, 38, 0))


def test_a_function_call_with_varargs_round_trips():
    """The *args branch of decode_artifact is a real construction path."""
    dialect = _dialect()
    expr = FunctionCall(dialect, "concat", Column(dialect, "a"), 18, "x")
    artifact = serialize(expr)
    restored = deserialize(artifact)

    assert isinstance(restored, FunctionCall)
    assert restored.func_name == "concat"
    assert isinstance(restored.args[1], type(expr.args[1]))
    assert restored.to_sql(dialect) == expr.to_sql(dialect)


def test_a_mapping_without_a_module_is_refused():
    registry = ExpressionRegistry({"bad": "NoDot"})
    with pytest.raises(RegistryError) as caught:
        registry.resolve_node("bad")
    assert "fully qualified" in str(caught.value)


def test_a_mapping_pointing_at_a_non_class_is_refused():
    target = "rhosocial.activerecord.backend.expression.core.__doc__"
    registry = ExpressionRegistry({"bad": target})
    with pytest.raises(RegistryError) as caught:
        registry.resolve_node("bad")
    assert "does not name a class" in str(caught.value)


def test_serializer_rejects_a_non_positive_depth():
    with pytest.raises(ValueError) as caught:
        ExpressionSerializer(max_depth=0)
    assert "positive" in str(caught.value)


def test_encode_refuses_a_node_whose_get_params_is_not_a_mapping():
    class BadNode(Column):
        def get_params(self):
            return ["not", "a", "dict"]

    with pytest.raises(ArtifactError) as caught:
        serialize(BadNode(_dialect(), "id"))
    assert "get_params() returned list" in str(caught.value)


def test_xml_round_trips_nested_containers_and_scalars():
    for value, expected in [
        (None, None),
        (True, True),
        (18, 18),
        (1.5, 1.5),
        ("abc", "abc"),
        (["a", 2], ["a", 2]),
        (("b", 3), ["b", 3]),  # tuples travel as arrays and read back as lists
        ({"x": [1, 2], "y": {"z": None}}, {"x": [1, 2], "y": {"z": None}}),
    ]:
        artifact = serialize_xml(Parameter(None, value))
        restored = deserialize_xml(artifact)
        assert isinstance(restored, Parameter)
        assert restored.value == expected


def test_xml_without_a_kind_is_refused():
    with pytest.raises(ArtifactError) as caught:
        deserialize_xml(b"<expression><params /></expression>")
    assert "kind" in str(caught.value)


def test_an_enum_parameter_is_carried_as_its_value():
    """Enums are str/int subclasses; the codec writes the JSON scalar they are."""
    import enum

    class Mode(str, enum.Enum):
        A = "a"

    artifact = serialize(Parameter(None, Mode.A))
    assert artifact["params"]["value"] == "a"
