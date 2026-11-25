# tests/rhosocial/activerecord_test/feature/migration/test_change_suggestion_consumption.py
"""A-side consumption of the four frozen change-plan suggestion points.

A lightweight dialect (or backend double) implements the minimal ``suggest_*``
protocols. Resolution appends only the expressions the backend actually
returned, and reports each tri-state answer without collapsing ``False`` into
``None``. No SQL is rendered or invented on this side.
"""

import dataclasses
from typing import Optional

import pytest

from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.statements import IndexDefinition
from rhosocial.activerecord.backend.expression.statements.ddl_partition import PartitionClause
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    TableConstraint,
    TableUniqueConstraint,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.suggestion import ColumnReorderSuggestion
from rhosocial.activerecord.migration import (
    AsyncMigrationContext,
    MigrationContext,
    plan_changes,
    resolve_point,
    resolve_suggestions,
)
from rhosocial.activerecord.model import ActiveRecord


class _Expr:
    """Minimal expression node: only ``to_sql`` is needed to be applicable."""

    def __init__(self, sql):
        self.sql = sql

    def to_sql(self):
        return self.sql, ()


class _SingleActionStatement:
    """A statement carrying exactly one action (still 1 expression -> 1 statement)."""

    def __init__(self, action):
        self.actions = [action]

    def to_sql(self):
        return "SINGLE", ()


class _MultiActionStatement:
    """A bundled statement the A side must refuse."""

    def __init__(self, *actions):
        self.actions = list(actions)

    def to_sql(self):
        return "MULTI", ()


class _Base(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "events"

    id: Optional[int] = None
    created_at: str = ""


class _Changed(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "events"

    __table_indexes__ = [IndexDefinition(None, name="idx_created", columns=["created_at"])]
    __table_constraints__ = [
        TableConstraint(
            None, branch=TableUniqueConstraint(None, ["created_at"]), name="uq_created"
        )
    ]

    @classmethod
    def table_partition(cls):
        return PartitionClause(None, "HASH", keys=[Column(None, "id")])

    created_at: str = ""
    id: Optional[int] = None


class _StubDialect:
    """Implements all four protocols; answers come from ``answers`` by label."""

    def __init__(self, answers=None):
        self.answers = answers or {}
        self.calls = []

    def _answer(self, label, point):
        self.calls.append((label, point))
        value = self.answers.get(label, None)
        if isinstance(value, tuple):
            return dataclasses.replace(point, operations=value)
        return value

    def suggest_column_reorder(self, point):
        return self._answer("column_reorder", point)

    def suggest_table_constraint_change(self, point):
        return self._answer("table_constraint_change", point)

    def suggest_table_index_change(self, point):
        return self._answer("table_index_change", point)

    def suggest_partition_scheme_change(self, point):
        return self._answer("partition_scheme_change", point)


def _plan():
    return plan_changes(_Base, _Changed, DummyDialect())


def _points(plan):
    return {point.label: point for point in plan.suggestion_points}


def _answer_all(expr_sql):
    return {
        "column_reorder": (_Expr(f"{expr_sql} reorder"),),
        "table_constraint_change": (_Expr(f"{expr_sql} constraint"),),
        "table_index_change": (_Expr(f"{expr_sql} index"),),
        "partition_scheme_change": (_Expr(f"{expr_sql} partition"),),
    }


def test_plan_changes_stays_explicit_about_suggestion_points():
    """Planning only describes the points; resolution is a separate step."""
    plan = _plan()
    assert plan.statements == []
    assert len(plan.suggestion_points) == 4
    assert all(point.operations is None for point in plan.suggestion_points)


def test_actions_are_appended_and_every_point_resolved():
    plan = _plan()
    dialect = _StubDialect(_answer_all("APPLY"))
    result = resolve_suggestions(plan, dialect)

    assert len(dialect.calls) == 4
    assert [label for label, _ in dialect.calls] == [
        "column_reorder",
        "table_constraint_change",
        "table_index_change",
        "partition_scheme_change",
    ]
    assert [statement.sql for statement in result.statements] == [
        "APPLY reorder",
        "APPLY constraint",
        "APPLY index",
        "APPLY partition",
    ]
    # The expressions land in the executable list, not a parallel one.
    assert plan.statements == result.statements
    assert len(result.resolved) == 4
    assert result.unresolved == []
    assert result.is_complete is True
    assert all(entry.state == "actions" for entry in result.entries)
    assert all(entry.is_actionable for entry in result.entries)
    assert all(
        entry.operations_or_none() == entry.operations for entry in result.entries
    )


def test_false_is_reported_unsupported_not_dropped():
    plan = _plan()
    expr = _Expr("REORDER")
    dialect = _StubDialect(
        {
            "column_reorder": (expr,),
            "table_constraint_change": False,
            "table_index_change": False,
            "partition_scheme_change": False,
        }
    )
    result = resolve_suggestions(plan, dialect)

    assert plan.statements == [expr]
    assert [entry.state for entry in result.entries] == [
        "actions",
        "unsupported",
        "unsupported",
        "unsupported",
    ]
    assert [entry.point.label for entry in result.unsupported] == [
        "table_constraint_change",
        "table_index_change",
        "partition_scheme_change",
    ]
    assert all(entry.operations_or_none() is None for entry in result.unsupported)
    assert False not in plan.statements
    assert result.is_complete is False


def test_none_is_reported_as_no_answer():
    point = ColumnReorderSuggestion()
    dialect = _StubDialect({"column_reorder": None})
    entry = resolve_point(point, dialect)

    assert entry.state == "no-answer"
    assert entry.is_actionable is False
    assert entry.operations == ()
    assert entry.operations_or_none() is None
    assert entry.point is point
    assert entry.protocol == "ColumnReorderSuggestionSupport"


def test_missing_protocol_is_reported_per_point():
    class _OnlyReorder:
        def suggest_column_reorder(self, point):
            return dataclasses.replace(point, operations=(_Expr("REORDER"),))

    plan = _plan()
    result = resolve_suggestions(plan, _OnlyReorder())

    assert [entry.state for entry in result.entries] == [
        "actions",
        "missing-protocol",
        "missing-protocol",
        "missing-protocol",
    ]
    assert [entry.protocol for entry in result.missing] == [
        "TableConstraintChangeSuggestionSupport",
        "TableIndexChangeSuggestionSupport",
        "PartitionSchemeChangeSuggestionSupport",
    ]
    assert [statement.sql for statement in plan.statements] == ["REORDER"]


def test_multi_action_statement_is_refused_naming_the_protocol():
    plan = _plan()
    dialect = _StubDialect(
        {"column_reorder": (_MultiActionStatement(_Expr("A"), _Expr("B")),)}
    )
    with pytest.raises(ValueError, match="ColumnReorderSuggestionSupport") as excinfo:
        resolve_suggestions(plan, dialect)
    assert "multi-action" in str(excinfo.value)
    assert plan.statements == []


def test_single_action_statement_is_accepted():
    point = ColumnReorderSuggestion()
    dialect = _StubDialect(
        {"column_reorder": (_SingleActionStatement(_Expr("A")),)}
    )
    entry = resolve_point(point, dialect)
    assert entry.state == "actions"
    assert len(entry.operations) == 1


def test_real_core_dialect_without_implementations_reports_honestly():
    """DummyDialect ships no change suggestion protocols: no crash, no guesses."""
    plan = _plan()
    result = resolve_suggestions(plan, DummyDialect())

    assert plan.statements == []
    assert result.statements == []
    assert len(result.missing) == 4
    assert result.unresolved == result.entries
    assert result.is_complete is False
    assert result.no_answer == []
    assert result.unsupported == []


def test_resolution_is_one_shot_per_point():
    plan = _plan()
    dialect = _StubDialect(_answer_all("APPLY"))
    first = resolve_suggestions(plan, dialect)
    second = resolve_suggestions(plan, dialect)

    assert len(plan.statements) == 4
    assert second.entries == []
    assert second.statements == []
    assert first.statements == plan.statements


class _DoubleBackend:
    """Lightweight backend carrying the protocols directly (no ``dialect``)."""

    def __init__(self):
        self.executed = []

    def execute(self, sql, params=None, options=None):
        self.executed.append(sql)

    def suggest_column_reorder(self, point):
        return dataclasses.replace(point, operations=(_Expr("REORDER"),))

    def suggest_table_constraint_change(self, point):
        return False

    def suggest_table_index_change(self, point):
        return None

    def suggest_partition_scheme_change(self, point):
        return dataclasses.replace(point, operations=(_Expr("PARTITION"),))


def test_context_change_accessors_return_tri_state_from_backend_double():
    ctx = MigrationContext(_DoubleBackend())
    points = _points(_plan())

    reorder = ctx.suggest_column_reorder(points["column_reorder"])
    assert reorder.state == "actions"
    assert [expr.sql for expr in reorder.operations] == ["REORDER"]

    constraint = ctx.suggest_table_constraint_change(points["table_constraint_change"])
    assert constraint.state == "unsupported"
    assert constraint.operations_or_none() is None

    index = ctx.suggest_table_index_change(points["table_index_change"])
    assert index.state == "no-answer"

    partition = ctx.suggest_partition_scheme_change(points["partition_scheme_change"])
    assert partition.state == "actions"
    assert [expr.sql for expr in partition.operations] == ["PARTITION"]


def test_context_can_apply_resolved_statements():
    backend = _DoubleBackend()
    ctx = MigrationContext(backend, dry_run=True)
    plan = _plan()
    result = ctx.resolve_suggestions(plan)

    assert [entry.state for entry in result.entries] == [
        "actions",
        "unsupported",
        "no-answer",
        "actions",
    ]
    assert ctx.apply(*plan.statements) == 2
    assert [sql for sql, _ in ctx.dry_run_sql] == ["REORDER", "PARTITION"]
    assert backend.executed == []


@pytest.mark.asyncio
async def test_async_context_resolves_and_applies_the_same_way():
    backend = _DoubleBackend()
    ctx = AsyncMigrationContext(backend, dry_run=True)
    plan = plan_changes(_Base, _Changed, DummyDialect())
    result = ctx.resolve_suggestions(plan)

    assert len(result.unsupported) == 1
    assert await ctx.apply(*plan.statements) == 2
    assert [sql for sql, _ in ctx.dry_run_sql] == ["REORDER", "PARTITION"]
