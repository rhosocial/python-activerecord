# tests/rhosocial/activerecord_test/feature/basic/ddl/test_partition_suggestion_outcome.py
"""The three partition-suggestion states must stay distinct when consumed."""

from rhosocial.activerecord.backend.expression import Column, PartitionByRangeClause
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.suggestion import PartitionBuildSuggestion
from rhosocial.activerecord.base.derivation import partition_suggestion_outcome
from rhosocial.activerecord.backend.suggestion.definitions import PartitionSuggestionOutcome


def _range_strategy():
    dialect = DummyDialect()
    return PartitionByRangeClause(dialect, [Column(dialect, "created_at")])


class _ActionsDialect(DummyDialect):
    """A dialect whose build suggestion offers a concrete expression chain."""

    def suggest_partition_build(self, strategy, plan):
        return PartitionBuildSuggestion(operations=(Column(self, "created_at"),))


def test_outcome_actions():
    outcome = partition_suggestion_outcome(_ActionsDialect(), "build", _range_strategy(), None)
    assert isinstance(outcome, PartitionSuggestionOutcome)
    assert outcome.state == "actions"
    assert outcome.is_actionable is True
    assert len(outcome.operations) == 1
    assert outcome.operations_or_none() == outcome.operations


def test_outcome_no_action():
    # Dummy answers None ("no action"), distinct from unsupported.
    outcome = partition_suggestion_outcome(DummyDialect(), "build", _range_strategy(), None)
    assert outcome.state == "no-action"
    assert outcome.is_actionable is False
    assert outcome.operations == ()
    assert outcome.operations_or_none() is None


def test_outcome_unsupported():
    # SQLite answers False ("explicitly unsupported") for table_alter.
    outcome = partition_suggestion_outcome(SQLiteDialect(), "table_alter", _range_strategy(), None)
    assert outcome.state == "unsupported"
    assert outcome.is_actionable is False
    assert outcome.operations_or_none() is None


def test_outcome_no_protocol():
    class _NoSuggestion:
        pass

    outcome = partition_suggestion_outcome(_NoSuggestion(), "build", _range_strategy(), None)
    assert outcome.state == "no-protocol"
    assert outcome.is_actionable is False


def test_unsupported_and_no_action_are_distinct():
    """The whole point: callers must tell 'unsupported' from 'no action'."""
    unsupported = partition_suggestion_outcome(
        SQLiteDialect(), "table_alter", _range_strategy(), None
    )
    no_action = partition_suggestion_outcome(DummyDialect(), "build", _range_strategy(), None)
    assert unsupported.state != no_action.state
    assert unsupported.state == "unsupported"
    assert no_action.state == "no-action"
