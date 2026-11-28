# tests/rhosocial/activerecord_test/feature/migration/test_change_outcome_api.py
"""User-facing schema/partition change outcomes and the shared apply guard.

Fake dialect/backend doubles stand in for real backends: core must classify
every point, refuse to fabricate partition DDL for engine-managed or
unpartitioned backends, and refuse destructive or bundled statements as a last
line of defence before execution.
"""
from __future__ import annotations

import dataclasses
from typing import Optional

import pytest

from rhosocial.activerecord.backend.dialect import PartitionCapability
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.bases.bases import BaseExpression
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import IndexDefinition
from rhosocial.activerecord.backend.expression.statements.ddl_partition import PartitionClause
from rhosocial.activerecord.backend.expression.statements.ddl_schema import (
    DropSchemaStatement,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    DropTableStatement,
    TableConstraint,
    TableUniqueConstraint,
)
from rhosocial.activerecord.backend.expression.statements.ddl_truncate import (
    TruncateStatement,
)
from rhosocial.activerecord.backend.expression.statements.dml import DeleteStatement
from rhosocial.activerecord.backend.expression.objects import Schema
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.suggestion import PartitionAddSuggestion
from rhosocial.activerecord.backend.suggestion.protocols import PartitionAddSuggestionSupport
from rhosocial.activerecord.migration import (
    AsyncMigrationContext,
    MigrationContext,
    PartitionChangeOutcome,
    SchemaChangeOutcome,
)
from rhosocial.activerecord.model import ActiveRecord


# -- Doubles -----------------------------------------------------------------

class _Expr(BaseExpression):
    """Minimal real expression node, acceptable to the raw outcome consumer."""

    def __init__(self, sql, kind=None):
        super().__init__(None)
        self.sql = sql
        self.kind = kind

    def to_sql(self):
        return self.sql, ()


class _MultiActionStatement:
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
        TableConstraint(None, branch=TableUniqueConstraint(None, ["created_at"]), name="uq_created")
    ]

    @classmethod
    def table_partition(cls):
        return PartitionClause(None, "HASH", keys=[Column(None, "id")])

    created_at: str = ""
    id: Optional[int] = None


class _ChangeDialect(DummyDialect):
    """A real planning dialect that answers three change protocols."""

    def __init__(self, answers=None):
        self.answers = answers or {}
        self.calls = []

    def _answer(self, label, point):
        self.calls.append(label)
        value = self.answers.get(label)
        if isinstance(value, tuple):
            return dataclasses.replace(point, operations=value)
        return value

    def suggest_column_reorder(self, point):
        return self._answer("column_reorder", point)

    def suggest_table_constraint_change(self, point):
        return self._answer("table_constraint_change", point)

    def suggest_table_index_change(self, point):
        return self._answer("table_index_change", point)


class _NoPartitionProtocolDialect(_ChangeDialect):
    """All change protocols except the partition-scheme one."""


class _SwitchDialect(DummyDialect):
    """Classifies an unpaired switch-out in its own (fake) vocabulary.

    A real backend answers from its own statement classes; this double answers
    from the statements' ``kind`` marker. The point of the test is that the
    context asks the dialect instead of reading SQL text.
    """

    def change_chain_refusals(self, statements, *, authorized_destructive=False):
        if authorized_destructive:
            return []
        outs = sum(1 for s in statements if getattr(s, "kind", None) == "out")
        ins = sum(1 for s in statements if getattr(s, "kind", None) == "in")
        if outs > ins:
            return ["refused data-moving SWITCH ... TO without a matching switch back"]
        return super().change_chain_refusals(statements)


class _Backend:
    def __init__(self, dialect=None):
        self.dialect = dialect
        self.executed = []

    def execute(self, sql, params=None, options=None):
        self.executed.append(sql)


class _AsyncBackend(_Backend):
    async def execute(self, sql, params=None, options=None):
        self.executed.append(sql)


class _PartitionDialect:
    """Implements the add-partition protocol and reports a chosen capability."""

    def __init__(self, capability, operations=None):
        self.capability = capability
        self.operations = operations
        self.calls = []

    def partition_capability(self):
        return self.capability

    def suggest_partition_add(self, strategy, plan):
        self.calls.append((strategy, plan))
        return PartitionAddSuggestion(operations=self.operations)


# -- Schema outcome ----------------------------------------------------------

def _mixed_outcome():
    """One point of each classification, in plan order."""
    expr = _Expr("REORDER")
    dialect = _NoPartitionProtocolDialect(
        {
            "column_reorder": (expr,),
            "table_constraint_change": False,
            "table_index_change": None,
        }
    )
    ctx = MigrationContext(_Backend(dialect))
    return ctx.plan_schema_change(_Base, _Changed), expr


def test_schema_outcome_classifies_all_four_points():
    outcome, expr = _mixed_outcome()

    assert outcome.statements == (expr,)
    assert [e.point.label for e in outcome.supported] == ["column_reorder"]
    assert [e.point.label for e in outcome.unsupported] == ["table_constraint_change"]
    assert [e.point.label for e in outcome.no_answer] == ["table_index_change"]
    assert [e.point.label for e in outcome.missing] == ["partition_scheme_change"]
    assert [e.protocol for e in outcome.missing] == ["PartitionSchemeChangeSuggestionSupport"]
    assert outcome.is_complete is False


def test_schema_outcome_report_names_reasons_without_sql():
    outcome, _ = _mixed_outcome()
    report = outcome.report()

    assert "1 executable statement(s)" in report
    assert "supported: 1 suggestion point(s)" in report
    assert "unsupported: table_constraint_change" in report
    assert "explicitly reported it cannot address the change" in report
    assert "no answer: table_index_change" in report
    assert "missing protocol: partition_scheme_change" in report
    assert "PartitionSchemeChangeSuggestionSupport" in report
    assert "REORDER" not in report


def test_schema_outcome_report_lists_supported_points():
    dialect = _NoPartitionProtocolDialect(
        {"column_reorder": (_Expr("R"),), "table_constraint_change": (_Expr("C"),),
         "table_index_change": (_Expr("I"),)}
    )
    outcome = MigrationContext(_Backend(dialect)).plan_schema_change(_Base, _Changed)
    assert len(outcome.supported) == 3
    assert "column_reorder via ColumnReorderSuggestionSupport" in outcome.report()
    assert "REORDER" not in outcome.report() and "\nR" not in outcome.report()


# -- Partition outcome -------------------------------------------------------

@pytest.mark.parametrize(
    ("capability", "state", "fragment"),
    [
        (PartitionCapability.AUTOMATIC, "engine-managed", "engine manages partitioning itself"),
        (PartitionCapability.UNSUPPORTED, "not-supported", "has no table partitioning"),
    ],
)
def test_unaddressable_capabilities_never_call_a_suggestion(capability, state, fragment):
    dialect = _PartitionDialect(capability, operations=(_Expr("FABRICATED"),))
    ctx = MigrationContext(_Backend(dialect))
    plan = object()
    strategy = object()

    outcome = ctx.plan_partition_change("add", strategy, plan)

    assert outcome.capability is capability
    assert outcome.operations is False
    assert outcome.state == state
    assert outcome.is_actionable is False
    assert outcome.is_complete is False
    assert dialect.calls == []
    assert "unaddressable" in outcome.report()
    assert fragment in outcome.report()
    assert ctx.apply_change(outcome, allow_incomplete=True) == 0


def test_native_capability_returns_operations_and_applies():
    expr = _Expr("ADD PARTITION")
    dialect = _PartitionDialect(PartitionCapability.NATIVE, operations=(expr,))
    backend = _Backend(dialect)
    ctx = MigrationContext(backend)
    strategy, plan = object(), object()

    outcome = ctx.plan_partition_change("add", strategy, plan)

    assert outcome.capability is PartitionCapability.NATIVE
    assert outcome.state == "actions"
    assert outcome.operations == (expr,)
    assert outcome.is_actionable is True
    assert outcome.is_complete is True
    assert dialect.calls == [(strategy, plan)]
    assert ctx.apply_change(outcome) == 1
    assert backend.executed == ["ADD PARTITION"]
    assert "1 operation(s) ready to apply" in outcome.report()


def test_native_tristate_is_preserved():
    expr = _Expr("ADD")
    cases = [
        ((expr,), "actions", (expr,), True),
        (None, "no-action", (), True),
        (False, "unsupported", False, False),
    ]
    for operations, state, expected, complete in cases:
        dialect = _PartitionDialect(PartitionCapability.NATIVE, operations=operations)
        outcome = MigrationContext(_Backend(dialect)).plan_partition_change(
            "add", object(), object()
        )
        assert outcome.state == state
        assert outcome.operations == expected
        assert outcome.is_complete is complete


def test_native_without_protocol_is_unaddressable():
    class _NoProtocol:
        def partition_capability(self):
            return PartitionCapability.NATIVE

    ctx = MigrationContext(_Backend(_NoProtocol()))
    outcome = ctx.plan_partition_change("add", object(), object())
    assert outcome.state == "no-protocol"
    assert outcome.operations is False
    assert "matching partition suggestion protocol" in outcome.report()


def test_unknown_intent_is_rejected_only_after_capability_gate():
    class _NoProtocol:
        def partition_capability(self):
            return PartitionCapability.AUTOMATIC

    ctx = MigrationContext(_Backend(_NoProtocol()))
    assert ctx.plan_partition_change("bogus", object(), object()).operations is False
    dialect = _PartitionDialect(PartitionCapability.NATIVE)
    with pytest.raises(ValueError, match="unknown partition change intent"):
        MigrationContext(_Backend(dialect)).plan_partition_change("bogus", object(), object())


# -- apply_change guard ------------------------------------------------------

def test_incomplete_outcome_is_refused_unless_allowed():
    outcome, expr = _mixed_outcome()
    backend = _Backend()
    ctx = MigrationContext(backend, dry_run=True)

    with pytest.raises(ValueError, match="allow_incomplete") as excinfo:
        ctx.apply_change(outcome)
    assert "unsupported: table_constraint_change" in str(excinfo.value)
    assert ctx.dry_run_sql == []

    assert ctx.apply_change(outcome, allow_incomplete=True) == 1
    assert ctx.dry_run_sql == [(expr.sql, ())]
    assert backend.executed == []


def _destructive_outcome(expr):
    return SchemaChangeOutcome(statements=(expr,))


@pytest.mark.parametrize(
    ("expr", "label"),
    [
        (
            DropTableStatement(DummyDialect(), Table(DummyDialect(), "events")),
            "DropTableStatement",
        ),
        (TruncateStatement(DummyDialect(), Table(DummyDialect(), "events")), "TruncateStatement"),
        (DeleteStatement(DummyDialect(), Table(DummyDialect(), "events")), "DeleteStatement"),
        (DropSchemaStatement(DummyDialect(), Schema(DummyDialect(), "app")), "DropSchemaStatement"),
    ],
)
def test_destructive_statements_are_refused_unless_authorized(expr, label):
    backend = _Backend()
    ctx = MigrationContext(backend)
    outcome = _destructive_outcome(expr)

    with pytest.raises(ValueError, match="refused destructive DDL") as excinfo:
        ctx.apply_change(outcome)
    assert label in str(excinfo.value)
    assert backend.executed == []

    assert ctx.apply_change(outcome, authorized_destructive=True) == 1
    assert len(backend.executed) == 1


def test_multi_action_statement_is_always_refused():
    expr = _MultiActionStatement(_Expr("A"), _Expr("B"))
    outcome = _destructive_outcome(expr)
    ctx = MigrationContext(_Backend())

    with pytest.raises(ValueError, match="one expression must map to exactly one action"):
        ctx.apply_change(outcome)
    with pytest.raises(ValueError, match="one expression must map to exactly one action"):
        ctx.apply_change(outcome, authorized_destructive=True)


def test_unbalanced_switch_is_refused_but_a_round_trip_is_allowed():
    """The backend classifies data-moving statements in its own vocabulary.

    The context never reads SQL text: it asks the dialect ``change_chain_refusals``,
    which here recognises the fake statements' own ``kind`` marker. A real backend
    (SQL Server) answers from its ``SWITCH PARTITION`` classes the same way.
    """
    switch_out = _Expr("out", kind="out")
    switch_back = _Expr("in", kind="in")
    backend = _Backend(_SwitchDialect())
    ctx = MigrationContext(backend)

    with pytest.raises(ValueError, match="SWITCH"):
        ctx.apply_change(_destructive_outcome(switch_out))
    assert backend.executed == []

    assert ctx.apply_change(
        SchemaChangeOutcome(statements=(switch_out, switch_back))
    ) == 2
    assert backend.executed == [switch_out.sql, switch_back.sql]


# -- Sync / async parity -----------------------------------------------------

def test_sync_context_applies_only_the_outcome_chain():
    expr = _Expr("R")
    dialect = _NoPartitionProtocolDialect({"column_reorder": (expr,)})
    backend = _Backend(dialect)
    ctx = MigrationContext(backend)

    outcome = ctx.plan_schema_change(_Base, _Changed)
    assert ctx.apply_change(outcome, allow_incomplete=True) == 1
    assert backend.executed == [expr.sql]


@pytest.mark.asyncio
async def test_async_context_matches_sync_planning_and_application():
    expr = _Expr("R")
    dialect = _NoPartitionProtocolDialect({"column_reorder": (expr,)})
    backend = _AsyncBackend(dialect)
    ctx = AsyncMigrationContext(backend)

    outcome = ctx.plan_schema_change(_Base, _Changed)
    assert [e.point.label for e in outcome.missing] == ["partition_scheme_change"]
    assert [e.point.label for e in outcome.no_answer] == [
        "table_constraint_change", "table_index_change"
    ]
    assert await ctx.apply_change(outcome, allow_incomplete=True) == 1
    assert backend.executed == [expr.sql]

    partition = _PartitionDialect(PartitionCapability.AUTOMATIC, operations=(_Expr("X"),))
    pctx = AsyncMigrationContext(_AsyncBackend(partition))
    poutcome = pctx.plan_partition_change("add", object(), object())
    assert poutcome.operations is False
    assert partition.calls == []
    assert await pctx.apply_change(poutcome, allow_incomplete=True) == 0


@pytest.mark.asyncio
async def test_async_guard_refuses_the_same_destructive_statement():
    ctx = AsyncMigrationContext(_AsyncBackend())
    expr = DeleteStatement(DummyDialect(), Table(DummyDialect(), "events"))
    with pytest.raises(ValueError, match="refused destructive DDL"):
        await ctx.apply_change(_destructive_outcome(expr))


def test_outcome_types_are_frozen():
    outcome = SchemaChangeOutcome()
    with pytest.raises(dataclasses.FrozenInstanceError):
        outcome.statements = ()

    partition = PartitionChangeOutcome(capability=PartitionCapability.NATIVE)
    with pytest.raises(dataclasses.FrozenInstanceError):
        partition.operations = ()


def test_partition_capability_protocol_remains_conformant():
    """The capability helper must read the protocol method, not a boolean."""
    assert isinstance(_PartitionDialect(PartitionCapability.NATIVE), PartitionAddSuggestionSupport)
    assert _PartitionDialect(PartitionCapability.AUTOMATIC).partition_capability() is (
        PartitionCapability.AUTOMATIC
    )
