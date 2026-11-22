# tests/rhosocial/activerecord_test/feature/expression/test_partition_expression_nodes.py
"""Phase 0 contracts for the expression-only partition nodes.

These dedicated strategy clauses and definition expressions are the
replacement for the legacy strategy enum and definition dataclasses.
They are real `BaseExpression` nodes: constructed with a dialect, rendering via
`format_method`, and carrying a plain-string `.word` for artifact serialization.
"""

import pytest

from rhosocial.activerecord.backend.expression import (
    Column,
    PartitionByHashClause,
    PartitionByListClause,
    PartitionByRangeClause,
    PartitionDefinitionExpression,
    PartitionOptionsExpression,
    SubpartitionDefinitionExpression,
)
from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.statements import PartitionClause
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


@pytest.fixture
def dialect():
    return DummyDialect()


@pytest.mark.parametrize(
    "cls,word",
    [
        (PartitionByRangeClause, "RANGE"),
        (PartitionByListClause, "LIST"),
        (PartitionByHashClause, "HASH"),
    ],
)
def test_strategy_clause_is_expression_with_fixed_word(dialect, cls, word):
    clause = cls(dialect, [Column(dialect, "id")])
    assert isinstance(clause, BaseExpression)
    assert isinstance(clause, PartitionClause)
    assert clause.method == word
    assert clause.WORD == word
    assert clause.format_method == "format_partition_clause"
    # artifact serialization: word is a plain str
    assert isinstance(clause.method, str)


def test_strategy_clause_rejects_empty_keys(dialect):
    with pytest.raises(ValueError):
        PartitionByRangeClause(dialect, [])


def test_definition_expression_is_renderable_node(dialect):
    de = PartitionDefinitionExpression(dialect, "p0", less_than=[Column(dialect, "id")])
    assert isinstance(de, BaseExpression)
    assert de.name == "p0"
    assert de.format_method == "format_partition_definition_expression"
    assert de.dialect is dialect


def test_definition_expression_validates_name_and_exclusive_boundaries(dialect):
    with pytest.raises(ValueError):
        PartitionDefinitionExpression(dialect, "  ")
    with pytest.raises(ValueError):
        PartitionDefinitionExpression(
            dialect, "p0", less_than=[Column(dialect, "id")], in_values=[Column(dialect, "id")]
        )


def test_subpartition_and_options_expressions(dialect):
    sub = SubpartitionDefinitionExpression(dialect, "sp0")
    assert isinstance(sub, BaseExpression)
    assert sub.format_method == "format_subpartition_definition_expression"
    opts = PartitionOptionsExpression(dialect, {"engine": "InnoDB"})
    assert isinstance(opts, BaseExpression)
    assert opts.format_method == "format_partition_options_expression"
    assert opts.options["engine"] == "InnoDB"
