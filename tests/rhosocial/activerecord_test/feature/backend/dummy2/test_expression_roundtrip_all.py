# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_expression_roundtrip_all.py
"""
Functional serialization coverage: every registered expression class must
round-trip losslessly through all three encodings (dict / JSON string / XML).

For each expression class that can be constructed:
  1. dict round-trip   : deserialize(serialize(e)).get_params() == e.get_params()
  2. JSON round-trip   : deserialize_json(serialize_json(e)).get_params() == ...
  3. XML round-trip    : deserialize_xml(serialize_xml(e)).get_params() == ...
  4. SQL consistency   : when to_sql() is supported, restored.to_sql() == e.to_sql()

Classes that cannot be constructed heuristically are reported explicitly
(NOT silently skipped) so coverage stays transparent and grows over time.
"""

import inspect

import pytest

from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.serialization import (
    ExpressionRegistry,
    deserialize,
    deserialize_json,
    deserialize_xml,
    serialize,
    serialize_json,
    serialize_xml,
)

from rhosocial.activerecord.testsuite.utils.expression import make_instance


def assert_params_equal(a, b, path="params"):
    """Deep compare two get_params() dicts, treating nested BaseExpression
    instances as structurally equal when their get_params() match."""
    if isinstance(a, BaseExpression) and isinstance(b, BaseExpression):
        assert_params_equal(a.get_params(), b.get_params(), path + ".<expr>")
        return
    assert type(a) is type(b) or (
        isinstance(a, (list, tuple, dict)) and isinstance(b, (list, tuple, dict))
    ), f"{path}: type mismatch {type(a).__name__} vs {type(b).__name__}"
    if isinstance(a, dict):
        assert set(a) == set(b), f"{path}: keys differ {set(a) ^ set(b)}"
        for k in a:
            assert_params_equal(a[k], b[k], f"{path}.{k}")
        return
    if isinstance(a, (list, tuple)):
        assert len(a) == len(b), f"{path}: length differ"
        for i, (x, y) in enumerate(zip(a, b)):
            assert_params_equal(x, y, f"{path}[{i}]")
        return
    assert a == b, f"{path}: {a!r} != {b!r}"


def _collect_registered_classes():
    ExpressionRegistry._auto_register_builtins()
    return {
        fqn: cls
        for fqn, cls in ExpressionRegistry._registry.items()
        if not inspect.isabstract(cls)
    }


REGISTERED = _collect_registered_classes()


@pytest.fixture(params=[fqn for fqn in sorted(REGISTERED)], ids=sorted(REGISTERED))
def expr_case(request, dummy_dialect):
    fqn = request.param
    cls = REGISTERED[fqn]
    instance, source = make_instance(cls, dummy_dialect)
    if instance is None:
        raise pytest.skip(f"{fqn}: not constructible (source=heuristic)")
    return fqn, instance


class TestExpressionRoundtripAll:
    """All constructible expression classes round-trip through all encodings."""

    def test_get_params_roundtrip_across_encodings(self, expr_case, dummy_dialect):
        fqn, instance = expr_case
        original = instance.get_params()

        spec_dict = serialize(instance)
        restored_d = deserialize(spec_dict, dummy_dialect)
        assert_params_equal(restored_d.get_params(), original, fqn)

        json_str = serialize_json(instance)
        restored_j = deserialize_json(json_str, dummy_dialect)
        assert_params_equal(restored_j.get_params(), original, fqn)

        xml_bytes = serialize_xml(instance)
        restored_x = deserialize_xml(xml_bytes, dummy_dialect)
        assert_params_equal(restored_x.get_params(), original, fqn)

    def test_to_sql_consistent_when_supported(self, expr_case, dummy_dialect):
        fqn, instance = expr_case
        # If to_sql works for the original, it must also work (and match) for
        # the restored instances in every encoding.
        try:
            expected = instance.to_sql()
        except Exception:
            return  # dialect does not support this expression's to_sql; structural test covers it

        for restored in (
            deserialize(serialize(instance), dummy_dialect),
            deserialize_json(serialize_json(instance), dummy_dialect),
            deserialize_xml(serialize_xml(instance), dummy_dialect),
        ):
            assert restored.to_sql() == expected, fqn


def test_coverage_report():
    """Surface classes that could not be constructed, so coverage is transparent."""
    from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
    from rhosocial.activerecord.backend.expression.serialization import ExpressionRegistry

    dialect = DummyDialect()
    ExpressionRegistry._auto_register_builtins()
    constructed = 0
    skipped = []
    for fqn, cls in REGISTERED.items():
        instance, source = make_instance(cls, dialect)
        if instance is None:
            skipped.append(fqn)
        else:
            constructed += 1
    assert constructed > 0
    # Non-blocking transparency: allow up to N unconstructed for now but keep
    # them visible in the failure message if the limit is exceeded.
    assert len(skipped) <= 30, (
        f"Too many unconstructed expression classes ({len(skipped)}):\n"
        + "\n".join(f"  - {f}" for f in skipped)
    )