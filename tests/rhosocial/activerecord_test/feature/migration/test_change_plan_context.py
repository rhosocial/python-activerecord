# tests/rhosocial/activerecord_test/feature/migration/test_change_plan_context.py
"""Rich, dialect-neutral declaration context on frozen change-plan points.

A frozen projection loses information a capable backend needs: column names
cannot rebuild a full column spec, and ``_freeze()`` collapses ``PRIMARY KEY``
and ``UNIQUE`` into the same ``{"columns": ...}`` tuple. These tests keep the
enriched context honest: the original projections and tri-state behaviour stay
unchanged, while a fake dialect can now build *real* core actions from the
live declaration objects the point carries.
"""
import dataclasses
from typing import Optional

import pytest

from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import IndexDefinition
from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
    AddTableConstraintAction,
    AlterTableStatement,
    ModifyColumnAction,
)
from rhosocial.activerecord.backend.expression.statements.ddl_partition import PartitionClause
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnDefinition,
    TableConstraint,
    TablePrimaryKeyConstraint,
    TableUniqueConstraint,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.suggestion import (
    ColumnReorderSuggestion,
    PartitionSchemeChangeSuggestion,
    TableConstraintChangeSuggestion,
    TableIndexChangeSuggestion,
)
from rhosocial.activerecord.migration import plan_changes, resolve_point
from rhosocial.activerecord.model import ActiveRecord


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


class _WithUnique(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "events"

    __table_constraints__ = [
        TableConstraint(
            None, branch=TableUniqueConstraint(None, ["created_at"]), name="uq_created"
        )
    ]

    id: Optional[int] = None
    created_at: str = ""


class _WithPrimary(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "events"

    __table_constraints__ = [
        TableConstraint(
            None, branch=TablePrimaryKeyConstraint(None, ["created_at"]), name="uq_created"
        )
    ]

    id: Optional[int] = None
    created_at: str = ""


class _WithIndex(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "events"

    __table_indexes__ = [IndexDefinition(None, name="idx_created", columns=["created_at"])]

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


def test_enriched_reorder_point_survives_planning_and_stays_frozen():
    plan = plan_changes(_Base, _Reordered, DummyDialect())
    point = _point(plan, ColumnReorderSuggestion)

    assert set(point.old_fields) == {"id", "created_at"}
    assert set(point.new_fields) == {"id", "created_at"}
    assert all(isinstance(c, ColumnDefinition) for c in point.old_fields.values())
    assert all(isinstance(c, ColumnDefinition) for c in point.new_fields.values())
    assert point.old_fields["id"].data_type is not None
    assert point.new_order == ("created_at", "id")

    # The point is still frozen and the declaration mapping is read-only.
    with pytest.raises(dataclasses.FrozenInstanceError):
        point.new_fields = {}
    with pytest.raises(TypeError):
        point.new_fields["id"] = None


def test_constraint_index_partition_points_carry_live_declarations():
    constraint = _point(
        plan_changes(_Base, _WithUnique, DummyDialect()), TableConstraintChangeSuggestion
    )
    assert isinstance(constraint.new_constraint_declarations[0], TableConstraint)
    assert isinstance(constraint.old_constraint_declarations, tuple)

    index = _point(
        plan_changes(_Base, _WithIndex, DummyDialect()), TableIndexChangeSuggestion
    )
    assert isinstance(index.new_index_declarations[0], IndexDefinition)
    assert index.new_index_declarations[0].name == "idx_created"

    partition = _point(
        plan_changes(_Base, _Partitioned, DummyDialect()), PartitionSchemeChangeSuggestion
    )
    assert isinstance(partition.new_partition_declaration, PartitionClause)


class _ReorderDialect:
    """A capable backend: rebuilds every column in the new order non-destructively."""

    def __init__(self, dialect):
        self.dialect = dialect

    def suggest_column_reorder(self, point):
        table = Table(self.dialect, point.table_name)
        chain = []
        previous = None
        for name in point.new_order:
            column = point.new_fields[name]
            chain.append(
                AlterTableStatement(
                    self.dialect,
                    table,
                    [
                        ModifyColumnAction(
                            self.dialect,
                            column,
                            first=previous is None,
                            after_column=previous,
                        )
                    ],
                )
            )
            previous = name
        return dataclasses.replace(point, operations=tuple(chain))


def test_fake_dialect_builds_a_real_non_destructive_reorder_chain():
    dialect = DummyDialect()
    point = _point(plan_changes(_Base, _Reordered, dialect), ColumnReorderSuggestion)

    entry = resolve_point(point, _ReorderDialect(dialect))
    assert entry.state == "actions"
    actions = [statement.actions[0] for statement in entry.operations]
    assert len(actions) == 2
    assert all(isinstance(action, ModifyColumnAction) for action in actions)
    assert actions[0].first is True and actions[0].after_column is None
    assert actions[1].first is False and actions[1].after_column == "created_at"
    # Real ColumnDefinitions are reused, not re-derived from names.
    assert actions[0].column is point.new_fields["created_at"]
    assert actions[1].column is point.new_fields["id"]
    assert actions[0].column.data_type is not None
    assert isinstance(actions[0].column.constraints, list)


def test_frozen_constraint_projections_collapse_but_live_branches_do_not():
    unique = _point(
        plan_changes(_Base, _WithUnique, DummyDialect()), TableConstraintChangeSuggestion
    )
    primary = _point(
        plan_changes(_Base, _WithPrimary, DummyDialect()), TableConstraintChangeSuggestion
    )
    # The two declarations differ only by branch kind, which _freeze() erases.
    assert unique.new_constraints == primary.new_constraints
    assert isinstance(unique.new_constraint_declarations[0].branch, TableUniqueConstraint)
    assert isinstance(primary.new_constraint_declarations[0].branch, TablePrimaryKeyConstraint)


class _ConstraintDialect:
    """A capable backend: adds the model's own constraint declaration as-is."""

    def __init__(self, dialect):
        self.dialect = dialect

    def suggest_table_constraint_change(self, point):
        declarations = point.new_constraint_declarations
        if not declarations:
            return False
        statement = AlterTableStatement(
            self.dialect,
            Table(self.dialect, point.table_name),
            [AddTableConstraintAction(self.dialect, declarations[0])],
        )
        return dataclasses.replace(point, operations=(statement,))


def test_fake_dialect_builds_a_real_add_constraint_action_preserving_branch():
    dialect = DummyDialect()
    point = _point(
        plan_changes(_Base, _WithUnique, dialect), TableConstraintChangeSuggestion
    )

    entry = resolve_point(point, _ConstraintDialect(dialect))
    assert entry.state == "actions"
    action = entry.operations[0].actions[0]
    assert isinstance(action, AddTableConstraintAction)
    assert isinstance(action.constraint.branch, TableUniqueConstraint)
    sql, _ = entry.operations[0].to_sql()
    assert "UNIQUE" in sql


def test_old_label_equality_and_tri_state_survive_enrichment():
    point = _point(
        plan_changes(_Base, _Reordered, DummyDialect()), ColumnReorderSuggestion
    )
    # Enrichment does not disturb string compatibility.
    assert point == "column_reorder"
    assert "column_reorder" == point
    assert dataclasses.replace(point, operations=(object(),)) == "column_reorder"

    # Tri-state is unchanged, including for points carrying live context.
    assert point.operations is None and point.state == "absent"
    assert ColumnReorderSuggestion(operations=False).state == "unaddressable"
    assert ColumnReorderSuggestion(operations=(object(),)).state == "actions"
    enriched = TableConstraintChangeSuggestion(
        new_constraint_declarations=(
            TableConstraint(None, branch=TableUniqueConstraint(None, ["a"])),
        )
    )
    assert enriched.state == "absent"
    assert dataclasses.replace(enriched, operations=False).state == "unaddressable"
