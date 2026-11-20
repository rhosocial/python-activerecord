# tests/rhosocial/activerecord_test/feature/basic/ddl/test_partition_table_suggestions.py
"""Contracts for partition table-drop/alter/split/merge suggestions (P2).

Same 8-part spec as the retention (B11) sample and P1 lifecycle points:
- minimal runtime-checkable protocols (one ``suggest_*`` method);
- frozen tri-state suggestion values (expression chain / False / None);
- no core default mixin;
- dummy gives the safe "no action" default (None);
- SQLite (no partitioning) answers explicit unsupported (False);
- consumption helpers gate on ``isinstance`` (structural no).
"""

import dataclasses

from rhosocial.activerecord.backend.dialect import mixins as core_mixins
from rhosocial.activerecord.backend.dialect.protocols import (
    PartitionTableDropSuggestionSupport,
    PartitionTableAlterSuggestionSupport,
    PartitionSplitSuggestionSupport,
    PartitionMergeSuggestionSupport,
)
from rhosocial.activerecord.backend.expression import (
    PartitionTableDropSuggestion,
    PartitionTableAlterSuggestion,
    PartitionSplitSuggestion,
    PartitionMergeSuggestion,
    partition_table_drop_parts,
    partition_table_alter_parts,
    partition_split_parts,
    partition_merge_parts,
)
from rhosocial.activerecord.backend.expression.statements import PartitionStrategy
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.mixins import (
    SQLitePartitionTableDropSuggestionMixin,
    SQLitePartitionTableAlterSuggestionMixin,
    SQLitePartitionSplitSuggestionMixin,
    SQLitePartitionMergeSuggestionMixin,
)

CASES = [
    (
        "table_drop",
        PartitionTableDropSuggestionSupport,
        PartitionTableDropSuggestion,
        partition_table_drop_parts,
        SQLitePartitionTableDropSuggestionMixin,
    ),
    (
        "table_alter",
        PartitionTableAlterSuggestionSupport,
        PartitionTableAlterSuggestion,
        partition_table_alter_parts,
        SQLitePartitionTableAlterSuggestionMixin,
    ),
    (
        "split",
        PartitionSplitSuggestionSupport,
        PartitionSplitSuggestion,
        partition_split_parts,
        SQLitePartitionSplitSuggestionMixin,
    ),
    (
        "merge",
        PartitionMergeSuggestionSupport,
        PartitionMergeSuggestion,
        partition_merge_parts,
        SQLitePartitionMergeSuggestionMixin,
    ),
]


def test_protocols_minimal_and_runtime_checkable():
    for name, proto, *_ in CASES:
        methods = [n for n in vars(proto) if not n.startswith("_")]
        assert methods == [f"suggest_partition_{name}"]
        assert isinstance(DummyDialect(), proto)
        assert isinstance(SQLiteDialect(), proto)


def test_suggestions_immutable_tri_state():
    for _, _, cls, *_ in CASES:
        s = cls()
        assert dataclasses.is_dataclass(s) and s.operations is None
        assert cls(False).operations is False
        try:
            s.operations = False  # type: ignore[misc]
        except dataclasses.FrozenInstanceError:
            pass
        else:
            raise AssertionError(f"{cls.__name__} must be frozen")


def test_core_ships_no_default_mixins():
    for _, _, cls, *_ in CASES:
        assert not hasattr(core_mixins, cls.__name__ + "Mixin")


def test_dummy_gives_safe_no_action_default():
    for name, *_ in CASES:
        suggestion = getattr(DummyDialect(), f"suggest_partition_{name}")(
            PartitionStrategy.RANGE, None
        )
        assert suggestion.operations is None


def test_sqlite_answers_explicit_unsupported():
    for name, _, _, _, sqlite_mixin in CASES:
        assert issubclass(SQLiteDialect, sqlite_mixin)
        suggestion = getattr(SQLiteDialect(), f"suggest_partition_{name}")(
            PartitionStrategy.RANGE, None
        )
        assert suggestion.operations is False


def test_helpers_return_none_for_no_answer_and_unsupported():
    for _, _, _, helper, _ in CASES:
        assert helper(DummyDialect(), PartitionStrategy.RANGE, None) is None
        assert helper(SQLiteDialect(), PartitionStrategy.RANGE, None) is None


def test_helpers_gate_on_structural_no():
    class _NoSuggestion:
        pass

    for _, _, _, helper, _ in CASES:
        assert helper(_NoSuggestion(), PartitionStrategy.RANGE, None) is None
