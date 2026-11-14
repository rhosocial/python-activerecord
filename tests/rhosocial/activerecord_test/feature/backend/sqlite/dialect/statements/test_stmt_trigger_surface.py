# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect/statements/test_stmt_trigger_surface.py
"""SQLite trigger DDL: row-level only, WHEN, UPDATE OF and IF [NOT] EXISTS."""

from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.objects import Function, Table, Trigger
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.statements import (
    CreateTriggerStatement,
    DropTriggerStatement,
    TriggerEvent,
    TriggerLevel,
    TriggerTiming,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

DIALECT = SQLiteDialect(version=(3, 53, 0))

TRUE_PROBES = (
    "supports_trigger",
    "supports_create_trigger",
    "supports_drop_trigger",
    "supports_instead_of_trigger",
    "supports_trigger_referencing",
    "supports_trigger_when",
    "supports_trigger_if_not_exists",
)


def test_trigger_capability_matrix():
    for name in TRUE_PROBES:
        assert getattr(DIALECT, name)() is True, name
    assert DIALECT.supports_statement_trigger() is False


def test_row_level_trigger_with_update_of_condition_and_if_not_exists():
    condition = ComparisonPredicate(
        DIALECT, "ne", Column(DIALECT, "new.status"), Column(DIALECT, "old.status")
    )
    sql, params = CreateTriggerStatement(
        DIALECT,
        trigger=Trigger(DIALECT, "keep_status"),
        table=Table(DIALECT, "orders"),
        timing=TriggerTiming.BEFORE,
        events=[TriggerEvent.UPDATE],
        update_columns=["status"],
        condition=condition,
        function=Function(DIALECT, "validate_status"),
        if_not_exists=True,
    ).to_sql()
    assert sql == (
        'CREATE TRIGGER IF NOT EXISTS "keep_status" BEFORE UPDATE OF "status" '
        'ON "orders" FOR EACH ROW WHEN ("new.status" <> "old.status") '
        'BEGIN SELECT "validate_status"(); END'
    )
    assert params == ()


def test_statement_level_trigger_omits_the_row_clause():
    sql, _ = CreateTriggerStatement(
        DIALECT,
        trigger=Trigger(DIALECT, "audit"),
        table=Table(DIALECT, "users"),
        timing=TriggerTiming.AFTER,
        events=[TriggerEvent.INSERT, TriggerEvent.DELETE],
        level=TriggerLevel.STATEMENT,
        function=Function(DIALECT, "record_change"),
    ).to_sql()
    assert "AFTER INSERT OR DELETE ON" in sql
    assert "FOR EACH ROW" not in sql
    assert sql.endswith('BEGIN SELECT "record_change"(); END')


def test_when_condition_parameters_travel_with_the_statement():
    condition = ComparisonPredicate(
        DIALECT, "gt", Column(DIALECT, "new.amount"), Literal(DIALECT, 100)
    )
    sql, params = CreateTriggerStatement(
        DIALECT,
        trigger=Trigger(DIALECT, "guard"),
        table=Table(DIALECT, "payments"),
        timing=TriggerTiming.BEFORE,
        events=[TriggerEvent.INSERT],
        condition=condition,
        function=Function(DIALECT, "check_amount"),
    ).to_sql()
    assert 'WHEN ("new.amount" > ?)' in sql
    assert params == (100,)


def test_drop_trigger_with_and_without_if_exists():
    with_exists = DropTriggerStatement(
        DIALECT, trigger=Trigger(DIALECT, "keep_status"), if_exists=True
    )
    assert with_exists.to_sql() == ('DROP TRIGGER IF EXISTS "keep_status"', ())

    plain = DropTriggerStatement(DIALECT, trigger=Trigger(DIALECT, "keep_status"))
    assert plain.to_sql() == ('DROP TRIGGER "keep_status"', ())
