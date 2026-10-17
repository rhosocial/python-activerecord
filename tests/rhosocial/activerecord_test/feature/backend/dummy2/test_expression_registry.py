# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_expression_registry.py
"""Tests for the expression registry contract (rules §7 / spec §5.5).

The registry only registers, checks and dispatches. This suite pins:

- registration is keyed by (dialect, kind) and a duplicate is an assembly-time
  hard failure, never a silent overwrite;
- "not registered" is the only unsupported state — there is no unknown kind;
- failures are one error class whose ``reason`` field is data, and the
  ``kind_not_registered`` message names both the kind and the dialect;
- a supports predicate affects judgement only, never registration, and a
  render that passed its predicate but refused fails fast with
  ``spec_invalid``;
- serialization does not consult the registry (a node carries its kind).
"""

import pytest

from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.registry import (
    default_registry,
    ExpressionRegistry,
    kind_of,
    RegistryError,
    RegistryReason,
)
from rhosocial.activerecord.backend.expression.serialization import serialize
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


def _render(expr):
    sql, params = expr.left.to_sql() if hasattr(expr, "left") else ("?", ())
    return sql, params


def _good_render(expr):
    return "1 = 1", ()


class _RejectingRender:
    """A render function that refuses a node despite a passing predicate."""

    def __call__(self, expr):
        raise ValueError("this combination is illegal")


class TestKindDerivation:
    def test_consecutive_capitals_are_one_word(self):
        class JSONValue(BaseExpression):
            pass

        assert kind_of(JSONValue) == "json_value"

    def test_simple_pascal_case(self):
        class ComparisonPredicate(BaseExpression):
            pass

        assert kind_of(ComparisonPredicate) == "comparison_predicate"


class TestRegistration:
    def test_register_and_invoke(self):
        registry = ExpressionRegistry()
        dialect = DummyDialect()

        registry.register(dialect, "comparison_predicate", _good_render)

        node = ComparisonPredicate(dialect, "=", Column(dialect, "a"), Column(dialect, "b"))
        assert registry.invoke(dialect, node) == ("1 = 1", ())

    def test_duplicate_registration_is_a_hard_failure(self):
        registry = ExpressionRegistry()
        dialect = DummyDialect()
        registry.register(dialect, "comparison_predicate", _good_render)

        with pytest.raises(RegistryError, match="already registered"):
            registry.register(dialect, "comparison_predicate", _good_render)

    def test_duplicate_failure_names_dialect_and_kind(self):
        registry = ExpressionRegistry()
        registry.register(DummyDialect(), "x_kind", _good_render)
        with pytest.raises(RegistryError) as exc_info:
            registry.register(DummyDialect(), "x_kind", _good_render)
        assert exc_info.value.kind == "x_kind"
        assert "DummyDialect" in str(exc_info.value)

    def test_different_dialects_do_not_collide(self):
        class OtherDialect(DummyDialect):
            pass

        registry = ExpressionRegistry()
        registry.register(DummyDialect(), "comparison_predicate", lambda e: ("A", ()))
        registry.register(OtherDialect(), "comparison_predicate", lambda e: ("B", ()))

        node = ComparisonPredicate(DummyDialect(), "=", Column(DummyDialect(), "a"), Column(DummyDialect(), "b"))
        assert registry.invoke(DummyDialect(), node) == ("A", ())
        assert registry.invoke(OtherDialect(), node) == ("B", ())

    def test_version_difference_does_not_affect_registration(self):
        """The same dialect class registers once; instances share the table."""
        registry = ExpressionRegistry()
        registry.register(DummyDialect, "comparison_predicate", _good_render)

        first = DummyDialect()
        second = DummyDialect()
        assert registry.supported_kinds(first) == registry.supported_kinds(second)


class TestCheckAndInvoke:
    def test_check_unregistered_is_false(self):
        registry = ExpressionRegistry()
        assert registry.check(DummyDialect(), "no_such_kind") is False

    def test_invoke_unregistered_names_kind_and_dialect(self):
        registry = ExpressionRegistry()
        dialect = DummyDialect()
        node = ComparisonPredicate(dialect, "=", Column(dialect, "a"), Column(dialect, "b"))

        with pytest.raises(RegistryError) as exc_info:
            registry.invoke(dialect, node)
        assert exc_info.value.reason is RegistryReason.KIND_NOT_REGISTERED
        assert exc_info.value.kind == "comparison_predicate"
        assert "DummyDialect" in str(exc_info.value)
        assert "comparison_predicate" in str(exc_info.value)

    def test_supported_predicate_declines_the_instance(self):
        registry = ExpressionRegistry()
        dialect = DummyDialect()
        node = ComparisonPredicate(dialect, "=", Column(dialect, "a"), Column(dialect, "b"))

        registry.register(
            dialect, "comparison_predicate", _good_render,
            supports=lambda n: False,
        )
        assert registry.check(dialect, "comparison_predicate", node) is False
        with pytest.raises(RegistryError) as exc_info:
            registry.invoke(dialect, node)
        assert exc_info.value.reason is RegistryReason.INSTANCE_UNSUPPORTED

    def test_predicate_true_but_render_refused_is_spec_invalid(self):
        """The predicate is an optimisation, not a guarantee."""
        registry = ExpressionRegistry()
        dialect = DummyDialect()
        node = ComparisonPredicate(dialect, "=", Column(dialect, "a"), Column(dialect, "b"))

        registry.register(
            dialect, "comparison_predicate", _RejectingRender(),
            supports=lambda n: True,
        )
        with pytest.raises(RegistryError) as exc_info:
            registry.invoke(dialect, node)
        assert exc_info.value.reason is RegistryReason.SPEC_INVALID

    def test_render_returning_a_wrong_shape_is_spec_invalid(self):
        registry = ExpressionRegistry()
        dialect = DummyDialect()
        node = ComparisonPredicate(dialect, "=", Column(dialect, "a"), Column(dialect, "b"))

        registry.register(dialect, "comparison_predicate", lambda e: "bare string")
        with pytest.raises(RegistryError) as exc_info:
            registry.invoke(dialect, node)
        assert exc_info.value.reason is RegistryReason.SPEC_INVALID

    def test_reason_is_data_not_text(self):
        registry = ExpressionRegistry()
        try:
            registry.invoke(DummyDialect(), ComparisonPredicate(
                DummyDialect(), "=", Column(DummyDialect(), "a"), Column(DummyDialect(), "b")
            ))
        except RegistryError as exc:
            assert isinstance(exc.reason, RegistryReason)
            assert exc.reason.value == "kind_not_registered"
        else:
            pytest.fail("expected RegistryError")


class TestRegistryBoundaries:
    def test_serialization_does_not_consult_the_registry(self):
        """An empty registry still serializes: the node carries its kind."""
        registry = ExpressionRegistry()  # nothing registered
        node = ComparisonPredicate(
            DummyDialect(), "=", Column(DummyDialect(), "a"), Column(DummyDialect(), "b")
        )
        spec = serialize(node)
        assert spec["type"].endswith(".ComparisonPredicate")
        # The empty registry answers no kinds at all — serialization did not
        # need it.
        assert registry.supported_kinds(DummyDialect()) == ()

    def test_default_registry_is_process_level(self):
        assert isinstance(default_registry, ExpressionRegistry)
