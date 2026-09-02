# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_expression_serializer_options.py
"""
Cover ExpressionSerializer configuration branches.

Targets uncovered lines in backend/expression/serialization.py:
- constructor validation (max_depth, warn_threshold)
- allowed_types allowlist (exact FQN + module wildcard + denial)
"""

import pytest

from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.expression.serialization import ExpressionSerializer
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


@pytest.fixture
def dialect():
    return DummyDialect()


class TestSerializerValidation:
    def test_invalid_max_depth(self):
        with pytest.raises(ValueError):
            ExpressionSerializer(max_depth=0)

    def test_invalid_warn_threshold_low(self):
        with pytest.raises(ValueError):
            ExpressionSerializer(warn_threshold=0)

    def test_invalid_warn_threshold_high(self):
        with pytest.raises(ValueError):
            ExpressionSerializer(warn_threshold=1.5)


class TestAllowedTypes:
    def test_exact_fqn_allowed(self, dialect):
        ser = ExpressionSerializer(allowed_types=[
            "rhosocial.activerecord.backend.expression.core.Literal"
        ])
        spec = ser.serialize(Literal(dialect, 1))
        restored = ser.deserialize(spec, dialect)
        assert restored.get_params() == Literal(dialect, 1).get_params()

    def test_wildcard_module_allowed(self, dialect):
        ser = ExpressionSerializer(allowed_types=[
            "rhosocial.activerecord.backend.expression.core.*"
        ])
        spec = ser.serialize(Literal(dialect, 1))
        restored = ser.deserialize(spec, dialect)
        assert restored is not None

    def test_denied_type_raises(self, dialect):
        ser = ExpressionSerializer(allowed_types=[
            "rhosocial.activerecord.backend.expression.predicates.*"
        ])
        spec = ser.serialize(Literal(dialect, 1))
        with pytest.raises(Exception):
            ser.deserialize(spec, dialect)
