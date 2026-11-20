# tests/rhosocial/activerecord_test/feature/basic/ddl/test_partition_retention_suggestion.py
"""Contracts for the partition-retention backend suggestion.

P0 sample of the backend-suggestion spec applied to migration (DDL/DML):
- the protocol is minimal (one ``suggest_*`` method) and runtime-checkable;
- the suggestion value is an immutable tri-state (expression chain / False / None);
- core ships no default mixin (a backend either implements or is structurally "no");
- dummy gives the safe "no action" default; SQLite (no partitioning) answers
  explicit "unsupported" (False);
- the consumption helper gates on ``isinstance`` and renders nothing on no-answer.
"""

import dataclasses

from rhosocial.activerecord.backend.dialect import mixins as core_mixins
from rhosocial.activerecord.backend.dialect.protocols import PartitionRetentionSuggestionSupport
from rhosocial.activerecord.backend.expression import (
    PartitionRetentionSuggestion,
    partition_retention_parts,
)
from rhosocial.activerecord.backend.expression.statements import PartitionStrategy
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.mixins import (
    SQLitePartitionRetentionSuggestionMixin,
)


def test_protocol_is_runtime_checkable_and_minimal():
    # one public method only -- no supports/format (backend-suggestion spec §9.4)
    methods = [n for n in vars(PartitionRetentionSuggestionSupport) if not n.startswith("_")]
    assert methods == ["suggest_partition_retention"]
    assert isinstance(DummyDialect(), PartitionRetentionSuggestionSupport)
    assert isinstance(SQLiteDialect(), PartitionRetentionSuggestionSupport)


def test_suggestion_is_immutable_tri_state():
    s = PartitionRetentionSuggestion()
    assert dataclasses.is_dataclass(s) and s.operations is None
    assert PartitionRetentionSuggestion(False).operations is False
    try:
        s.operations = False  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("suggestion must be frozen")


def test_core_ships_no_default_mixin():
    # a backend either implements the protocol itself or has no suggestion
    assert not hasattr(core_mixins, "PartitionRetentionSuggestionMixin")


def test_dummy_gives_safe_no_action_default():
    suggestion = DummyDialect().suggest_partition_retention(PartitionStrategy.RANGE, None)
    assert suggestion.operations is None


def test_sqlite_answers_explicit_unsupported():
    assert issubclass(SQLiteDialect, SQLitePartitionRetentionSuggestionMixin)
    suggestion = SQLiteDialect().suggest_partition_retention(PartitionStrategy.RANGE, None)
    # SQLite has no table partitioning -> explicit False (⊥), not silence
    assert suggestion.operations is False


def test_helper_returns_none_for_no_answer_and_unsupported():
    assert partition_retention_parts(DummyDialect(), PartitionStrategy.RANGE, None) is None
    assert partition_retention_parts(SQLiteDialect(), PartitionStrategy.RANGE, None) is None


def test_helper_gates_on_structural_no():
    class _NoSuggestion:
        pass

    # a dialect without the protocol is a structural "no", never an error
    assert partition_retention_parts(_NoSuggestion(), PartitionStrategy.RANGE, None) is None
