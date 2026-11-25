# tests/rhosocial/activerecord_test/feature/migration/test_change_plan_suggestions.py
"""Frozen tri-state suggestion contract for the four multi-step change points.

Core declares only the data shapes and the minimal ``suggest_*`` protocols;
backend implementation and A-side consumption are deliberately out of scope.
"""
import dataclasses
from typing import Optional, Protocol

from rhosocial.activerecord.backend.dialect import mixins as core_mixins
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.statements import IndexDefinition
from rhosocial.activerecord.backend.expression.statements.ddl_partition import PartitionClause
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    TableConstraint,
    TableUniqueConstraint,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.suggestion import (
    ColumnReorderSuggestion,
    PartitionSchemeChangeSuggestion,
    TableConstraintChangeSuggestion,
    TableIndexChangeSuggestion,
)
from rhosocial.activerecord.backend.suggestion.protocols import (
    ColumnReorderSuggestionSupport,
    PartitionSchemeChangeSuggestionSupport,
    TableConstraintChangeSuggestionSupport,
    TableIndexChangeSuggestionSupport,
)
from rhosocial.activerecord.migration import plan_changes
from rhosocial.activerecord.model import ActiveRecord

CASES = [
    ("column_reorder", ColumnReorderSuggestion, ColumnReorderSuggestionSupport,
     "suggest_column_reorder"),
    ("table_constraint_change", TableConstraintChangeSuggestion,
     TableConstraintChangeSuggestionSupport, "suggest_table_constraint_change"),
    ("table_index_change", TableIndexChangeSuggestion, TableIndexChangeSuggestionSupport,
     "suggest_table_index_change"),
    ("partition_scheme_change", PartitionSchemeChangeSuggestion,
     PartitionSchemeChangeSuggestionSupport, "suggest_partition_scheme_change"),
]


def test_all_four_suggestions_are_frozen_tri_state():
    for label, cls, _, _ in CASES:
        point = cls()
        assert dataclasses.is_dataclass(point)
        assert point.label == label
        assert point.operations is None
        assert point.state == "absent"
        assert cls(operations=False).state == "unaddressable"
        assert cls(operations=(object(),)).state == "actions"
        try:
            point.operations = False  # type: ignore[misc]
        except dataclasses.FrozenInstanceError:
            pass
        else:
            raise AssertionError(f"{cls.__name__} must be frozen")


def test_all_four_protocols_are_minimal_and_runtime_checkable():
    for label, _, proto, method in CASES:
        own_methods = [name for name in vars(proto) if not name.startswith("_")]
        assert own_methods == [f"suggest_{label}"], own_methods
        assert method == f"suggest_{label}"
        assert issubclass(proto, Protocol)
        assert getattr(proto, "_is_runtime_protocol", False)


def test_core_ships_no_default_mixins():
    for _, cls, _, _ in CASES:
        assert not hasattr(core_mixins, cls.__name__.replace("Suggestion", "SuggestionMixin"))


def test_suggestion_points_compare_equal_to_their_old_labels():
    """Backward compatibility for callers that checked bare strings."""
    for label, cls, _, _ in CASES:
        point = cls()
        assert point == label
        assert label == point


class _Base(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "events"

    id: Optional[int] = None
    created_at: str = ""


class _Reordered(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "events"

    created_at: str = ""
    id: Optional[int] = None


class _WithIndex(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "events"

    __table_indexes__ = [IndexDefinition(None, name="idx_created", columns=["created_at"])]

    id: Optional[int] = None
    created_at: str = ""


class _WithConstraint(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "events"

    __table_constraints__ = [
        TableConstraint(None, branch=TableUniqueConstraint(None, ["created_at"]),
                        name="uq_created"),
    ]

    id: Optional[int] = None
    created_at: str = ""


class _Partitioned(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "events"

    @classmethod
    def table_partition(cls):
        return PartitionClause(None, "HASH", keys=[Column(None, "id")])

    id: Optional[int] = None
    created_at: str = ""


def _point(plan, typ):
    return next(p for p in plan.suggestion_points if isinstance(p, typ))


def test_plan_populates_column_reorder_point_with_names():
    plan = plan_changes(_Base, _Reordered, DummyDialect())
    point = _point(plan, ColumnReorderSuggestion)
    assert point.table_name == "events"
    assert set(point.reordered_columns) == {"id", "created_at"}
    assert point.old_order == ("id", "created_at")
    assert point.new_order == ("created_at", "id")
    assert point.operations is None


def test_plan_populates_constraint_point_with_frozen_projections():
    plan = plan_changes(_Base, _WithConstraint, DummyDialect())
    point = _point(plan, TableConstraintChangeSuggestion)
    assert point.table_name == "events"
    assert point.old_constraints == ()
    assert point.new_constraints  # frozen projection of the declared constraint


def test_plan_populates_index_point_with_frozen_projections():
    plan = plan_changes(_Base, _WithIndex, DummyDialect())
    point = _point(plan, TableIndexChangeSuggestion)
    assert point.table_name == "events"
    assert point.old_indexes == ()
    assert point.new_indexes  # frozen projection of the declared index


def test_plan_populates_partition_point_with_frozen_projections():
    plan = plan_changes(_Base, _Partitioned, DummyDialect())
    point = _point(plan, PartitionSchemeChangeSuggestion)
    assert point.table_name == "events"
    assert point.old_partition is None
    assert point.new_partition is not None
