# tests/rhosocial/activerecord_test/feature/basic/ddl/test_ddl_partition_expressions.py
"""Tests for generic partition expression declarations and rendering."""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.dialect.mixins.partition import PartitionMixin
from rhosocial.activerecord.backend.expression import (
    Column,
    PartitionByHashClause,
    PartitionByListClause,
    PartitionByRangeClause,
    PartitionClause,
    PartitionDefinitionExpression,
    SubpartitionDefinitionExpression,
)
from rhosocial.activerecord.backend.impl.dummy.backend import DummyDialect


class PartitionDialect(DummyDialect):
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


@pytest.fixture
def dummy():
    return DummyDialect()


@pytest.fixture
def partition_dialect():
    return PartitionDialect()


def test_partition_definition_minimal(dummy):
    definition = PartitionDefinitionExpression(dummy, "p0")
    assert definition.name == "p0"
    assert definition.less_than is None
    assert definition.in_values is None


def test_partition_definition_rejects_empty_name(dummy):
    with pytest.raises(ValueError, match="non-empty string"):
        PartitionDefinitionExpression(dummy, "   ")


def test_partition_definition_rejects_both_boundaries(dummy):
    with pytest.raises(ValueError, match="mutually exclusive"):
        PartitionDefinitionExpression(dummy, "p0", less_than=[], in_values=[])


def test_partition_definition_subclass_is_instance(dummy):
    class BackendDefinitionExpression(PartitionDefinitionExpression):
        pass

    assert isinstance(BackendDefinitionExpression(dummy, "p0"), PartitionDefinitionExpression)


def test_subpartition_definition_minimal(dummy):
    definition = SubpartitionDefinitionExpression(dummy, "sp0")
    assert definition.name == "sp0"


def test_subpartition_definition_rejects_empty_name(dummy):
    with pytest.raises(ValueError, match="non-empty string"):
        SubpartitionDefinitionExpression(dummy, "")


@pytest.mark.parametrize(
    "clause_cls,word",
    [
        (PartitionByRangeClause, "RANGE"),
        (PartitionByListClause, "LIST"),
        (PartitionByHashClause, "HASH"),
    ],
)
def test_generic_partition_clause_renders(partition_dialect, clause_cls, word):
    clause = clause_cls(partition_dialect, [Column(partition_dialect, "created_at")])
    sql, params = clause.to_sql()
    assert sql == f' PARTITION BY {word} ("created_at")'
    assert params == ()


def test_generic_partition_clause_multiple_keys(partition_dialect):
    clause = PartitionByRangeClause(
        partition_dialect,
        [Column(partition_dialect, "a"), Column(partition_dialect, "b")],
    )
    sql, _ = clause.to_sql()
    assert sql == ' PARTITION BY RANGE ("a", "b")'


def test_generic_partition_clause_unsupported_method(partition_dialect):
    clause = PartitionClause(
        partition_dialect,
        "KEY",
        [Column(partition_dialect, "a")],
    )
    with pytest.raises(UnsupportedFeatureError, match="KEY"):
        partition_dialect.format_partition_clause(clause)


def test_generic_partition_clause_method_gate():
    class RangeOnlyDialect(PartitionDialect):
        def supports_list_table_partitioning(self) -> bool:
            return False

    dialect = RangeOnlyDialect()
    clause = PartitionByListClause(dialect, [Column(dialect, "a")])
    with pytest.raises(UnsupportedFeatureError, match="LIST"):
        dialect.format_partition_clause(clause)


def test_generic_partition_clause_unsupported_dialect(dummy):
    clause = PartitionByRangeClause(dummy, [Column(dummy, "a")])
    with pytest.raises(UnsupportedFeatureError):
        dummy.format_partition_clause(clause)


def test_generic_format_partition_definition_fails_fast():
    class DefinitionMixinDialect(PartitionMixin):
        name = "definition-mixin"

    dialect = DefinitionMixinDialect()
    definition = PartitionDefinitionExpression(DummyDialect(), "p0")
    with pytest.raises(UnsupportedFeatureError, match="partition definition"):
        dialect.format_partition_definition(definition)
