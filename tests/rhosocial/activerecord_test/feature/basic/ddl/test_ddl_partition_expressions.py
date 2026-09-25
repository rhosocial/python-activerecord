# tests/rhosocial/activerecord_test/feature/basic/ddl/test_ddl_partition_expressions.py
"""Tests for the generic partition DDL expressions.

Covers the structural ``PartitionDefinition`` / ``SubpartitionDefinition``
base declarations and the generic ``PartitionClause`` rendering (clause-only)
provided by ``PartitionMixin``.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.dialect.mixins.partition import PartitionMixin
from rhosocial.activerecord.backend.expression import (
    Column,
    PartitionClause,
    PartitionDefinition,
    PartitionStrategy,
    SubpartitionDefinition,
)
from rhosocial.activerecord.backend.impl.dummy import DummyDialect
from rhosocial.activerecord.ddl import (
    PartitionCapabilities,
    PartitionLifecycle,
    PartitionOperation,
    PartitionOperationNotSupportedError,
)


class _PartitionDialect(DummyDialect):
    """Dummy dialect that advertises generic RANGE/LIST/HASH partitioning."""

    def supports_table_partitioning(self) -> bool:
        return True

    def supports_partitioned_table_creation(self) -> bool:
        return True

    def supports_range_table_partitioning(self) -> bool:
        return True

    def supports_list_table_partitioning(self) -> bool:
        return True

    def supports_hash_table_partitioning(self) -> bool:
        return True


class _LifecycleSource:
    @classmethod
    def table_name(cls):
        return "events"

    @classmethod
    def schema_name(cls):
        return None


class _LifecycleProvider:
    def __init__(self, dialect):
        self.dialect = dialect
        self.request = None

    def capabilities(self):
        return PartitionCapabilities(
            frozenset({PartitionOperation.CREATE, PartitionOperation.DROP}),
            ("RANGE",),
        )

    def supports(self, operation):
        return operation in {PartitionOperation.CREATE, PartitionOperation.DROP}

    def build(self, request):
        from rhosocial.activerecord.backend.expression.core import TableExpression

        self.request = request
        return TableExpression(self.dialect, request.table.name)


class _LifecycleDialect(DummyDialect):
    def __init__(self):
        super().__init__()
        self.lifecycle_provider = _LifecycleProvider(self)

    def get_partition_lifecycle_provider(self):
        return self.lifecycle_provider


@pytest.fixture
def dummy():
    return DummyDialect()


@pytest.fixture
def partition_dialect():
    return _PartitionDialect()


# ---------------------------------------------------------------------------
# PartitionDefinition
# ---------------------------------------------------------------------------


def test_partition_definition_minimal():
    definition = PartitionDefinition(name="p0")
    assert definition.name == "p0"
    assert definition.less_than is None
    assert definition.in_values is None


def test_partition_definition_rejects_empty_name():
    with pytest.raises(ValueError, match="non-empty string"):
        PartitionDefinition(name="   ")


def test_partition_definition_rejects_both_boundaries():
    with pytest.raises(ValueError, match="mutually exclusive"):
        PartitionDefinition(name="p0", less_than=[], in_values=[])


def test_partition_definition_rejects_non_dict_options():
    with pytest.raises(TypeError, match="dialect_options"):
        PartitionDefinition(name="p0", dialect_options=[])


def test_partition_definition_subclass_is_instance():
    class BackendPartitionDefinition(PartitionDefinition):
        pass

    assert isinstance(BackendPartitionDefinition(name="p0"), PartitionDefinition)


# ---------------------------------------------------------------------------
# SubpartitionDefinition
# ---------------------------------------------------------------------------


def test_subpartition_definition_minimal():
    definition = SubpartitionDefinition(name="sp0")
    assert definition.name == "sp0"


def test_subpartition_definition_rejects_empty_name():
    with pytest.raises(ValueError, match="non-empty string"):
        SubpartitionDefinition(name="")


def test_subpartition_definition_rejects_non_dict_options():
    with pytest.raises(TypeError, match="dialect_options"):
        SubpartitionDefinition(name="sp0", dialect_options=[])


# ---------------------------------------------------------------------------
# Generic PartitionClause rendering
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("strategy", [PartitionStrategy.RANGE, PartitionStrategy.LIST, PartitionStrategy.HASH])
def test_generic_partition_clause_renders(partition_dialect, strategy):
    clause = PartitionClause(
        partition_dialect, strategy, [Column(partition_dialect, "created_at")]
    )
    sql, params = clause.to_sql()
    assert sql == f" PARTITION BY {strategy.value} (\"created_at\")"
    assert params == ()


def test_generic_partition_clause_multiple_keys(partition_dialect):
    clause = PartitionClause(
        partition_dialect,
        PartitionStrategy.RANGE,
        [Column(partition_dialect, "a"), Column(partition_dialect, "b")],
    )
    sql, _ = clause.to_sql()
    assert sql == ' PARTITION BY RANGE ("a", "b")'


def test_generic_partition_clause_unsupported_method(partition_dialect):
    clause = PartitionClause(
        partition_dialect, PartitionStrategy.RANGE, [Column(partition_dialect, "a")]
    )
    clause.method = "KEY"
    with pytest.raises(UnsupportedFeatureError, match="KEY"):
        partition_dialect.format_partition_clause(clause)


def test_generic_partition_clause_method_gate():
    class RangeOnlyDialect(_PartitionDialect):
        def supports_list_table_partitioning(self) -> bool:
            return False

    dialect = RangeOnlyDialect()
    clause = PartitionClause(dialect, PartitionStrategy.LIST, [Column(dialect, "a")])
    with pytest.raises(UnsupportedFeatureError, match="LIST"):
        dialect.format_partition_clause(clause)


def test_generic_partition_clause_unsupported_dialect(dummy):
    clause = PartitionClause(dummy, PartitionStrategy.RANGE, [Column(dummy, "a")])
    with pytest.raises(UnsupportedFeatureError):
        dummy.format_partition_clause(clause)


# ---------------------------------------------------------------------------
# Generic partition definition is not renderable
# ---------------------------------------------------------------------------


def test_generic_format_partition_definition_fails_fast():
    class DefinitionMixinDialect(PartitionMixin):
        name = "definition-mixin"

    dialect = DefinitionMixinDialect()
    with pytest.raises(UnsupportedFeatureError, match="partition definition"):
        dialect.format_partition_definition(PartitionDefinition(name="p0"))


def test_partition_lifecycle_uses_explicit_provider():
    lifecycle = PartitionLifecycle(_LifecycleSource, _LifecycleDialect())
    assert lifecycle.capabilities().supports(PartitionOperation.DROP)
    assert lifecycle.drop_partition("p0").name == "events"


def test_partition_lifecycle_fails_without_provider():
    lifecycle = PartitionLifecycle(_LifecycleSource, DummyDialect())
    with pytest.raises(PartitionOperationNotSupportedError):
        lifecycle.drop_partition("p0")


def test_create_partition_forwards_clause_and_schema_overrides():
    dialect = _LifecycleDialect()
    lifecycle = PartitionLifecycle(_LifecycleSource, dialect)
    clause = PartitionClause(
        dialect,
        PartitionStrategy.LIST,
        [Column(dialect, "region")],
    )

    lifecycle.create_partition(
        "events_emea",
        "RANGE",
        {"from": "2026-01-01", "to": "2027-01-01"},
        partition_clause=clause,
        partition_schema="events_child",
        parent_schema="events_parent",
    )

    request = dialect.lifecycle_provider.request
    assert request.partition_clause is clause
    assert request.partition_schema == "events_child"
    assert request.parent_schema == "events_parent"
