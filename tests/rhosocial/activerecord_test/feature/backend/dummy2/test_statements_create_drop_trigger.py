# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_create_drop_trigger.py
from rhosocial.activerecord.backend.expression.statements import (
    CreateTriggerExpression,
    DropTriggerExpression,
    TriggerTiming,
    TriggerEvent,
    TriggerLevel,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression.objects import Function, Table
from rhosocial.activerecord.backend.expression.objects import Trigger


class TestCreateTriggerStatements:
    """Tests for CREATE TRIGGER statements."""

    def test_basic_create_trigger_before_insert(self, dummy_dialect: DummyDialect):
        """Tests basic CREATE TRIGGER BEFORE INSERT."""
        create_trigger = CreateTriggerExpression(
            dummy_dialect,
            trigger=Trigger(dummy_dialect, "before_insert_trigger"),
            table=Table(dummy_dialect, "users"),
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.INSERT],
            function=Function(dummy_dialect, "set_created_at"),
        )
        sql, params = create_trigger.to_sql()

        assert "CREATE TRIGGER" in sql
        assert '"before_insert_trigger"' in sql
        assert "BEFORE" in sql
        assert "INSERT" in sql
        assert "ON" in sql
        assert '"users"' in sql
        assert "FOR EACH ROW" in sql
        assert "EXECUTE" in sql
        assert '"set_created_at"' in sql
        assert params == ()

    def test_create_trigger_after_update(self, dummy_dialect: DummyDialect):
        """Tests CREATE TRIGGER AFTER UPDATE."""
        create_trigger = CreateTriggerExpression(
            dummy_dialect,
            trigger=Trigger(dummy_dialect, "after_update_trigger"),
            table=Table(dummy_dialect, "orders"),
            timing=TriggerTiming.AFTER,
            events=[TriggerEvent.UPDATE],
            function=Function(dummy_dialect, "log_update"),
        )
        sql, params = create_trigger.to_sql()

        assert "AFTER" in sql
        assert "UPDATE" in sql
        assert params == ()

    def test_create_trigger_after_delete(self, dummy_dialect: DummyDialect):
        """Tests CREATE TRIGGER AFTER DELETE."""
        create_trigger = CreateTriggerExpression(
            dummy_dialect,
            trigger=Trigger(dummy_dialect, "after_delete_trigger"),
            table=Table(dummy_dialect, "logs"),
            timing=TriggerTiming.AFTER,
            events=[TriggerEvent.DELETE],
            function=Function(dummy_dialect, "cleanup_old_logs"),
        )
        sql, params = create_trigger.to_sql()

        assert "AFTER" in sql
        assert "DELETE" in sql

    def test_create_trigger_instead_of(self, dummy_dialect: DummyDialect):
        """Tests CREATE TRIGGER INSTEAD OF (for views)."""
        create_trigger = CreateTriggerExpression(
            dummy_dialect,
            trigger=Trigger(dummy_dialect, "instead_of_insert"),
            table=Table(dummy_dialect, "user_view"),
            timing=TriggerTiming.INSTEAD_OF,
            events=[TriggerEvent.INSERT],
            function=Function(dummy_dialect, "handle_insert"),
        )
        sql, params = create_trigger.to_sql()

        assert "INSTEAD OF" in sql

    def test_create_trigger_if_not_exists(self, dummy_dialect: DummyDialect):
        """Tests CREATE TRIGGER IF NOT EXISTS."""
        create_trigger = CreateTriggerExpression(
            dummy_dialect,
            trigger=Trigger(dummy_dialect, "some_trigger"),
            table=Table(dummy_dialect, "t"),
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.INSERT],
            function=Function(dummy_dialect, "f"),
            if_not_exists=True,
        )
        sql, params = create_trigger.to_sql()

        assert "IF NOT EXISTS" in sql

    def test_create_trigger_multiple_events(self, dummy_dialect: DummyDialect):
        """Tests CREATE TRIGGER with multiple events."""
        create_trigger = CreateTriggerExpression(
            dummy_dialect,
            trigger=Trigger(dummy_dialect, "multi_event_trigger"),
            table=Table(dummy_dialect, "audit"),
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.INSERT, TriggerEvent.UPDATE, TriggerEvent.DELETE],
            function=Function(dummy_dialect, "log_change"),
        )
        sql, params = create_trigger.to_sql()

        assert "INSERT OR UPDATE OR DELETE" in sql

    def test_create_trigger_update_of_columns(self, dummy_dialect: DummyDialect):
        """Tests CREATE TRIGGER with UPDATE OF column_list."""
        create_trigger = CreateTriggerExpression(
            dummy_dialect,
            trigger=Trigger(dummy_dialect, "update_columns_trigger"),
            table=Table(dummy_dialect, "orders"),
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.UPDATE],
            update_columns=["status", "amount"],
            function=Function(dummy_dialect, "validate_update"),
        )
        sql, params = create_trigger.to_sql()

        assert "UPDATE OF" in sql
        assert '"status"' in sql
        assert '"amount"' in sql

    def test_create_trigger_statement_level(self, dummy_dialect: DummyDialect):
        """Tests CREATE TRIGGER with FOR EACH STATEMENT."""
        create_trigger = CreateTriggerExpression(
            dummy_dialect,
            trigger=Trigger(dummy_dialect, "statement_trigger"),
            table=Table(dummy_dialect, "logs"),
            timing=TriggerTiming.AFTER,
            events=[TriggerEvent.INSERT],
            function=Function(dummy_dialect, "count_inserts"),
            level=TriggerLevel.STATEMENT,
        )
        sql, params = create_trigger.to_sql()

        assert "FOR EACH STATEMENT" in sql

    def test_create_trigger_with_referencing(self, dummy_dialect: DummyDialect):
        """Tests CREATE TRIGGER with REFERENCING clause."""
        create_trigger = CreateTriggerExpression(
            dummy_dialect,
            trigger=Trigger(dummy_dialect, "referencing_trigger"),
            table=Table(dummy_dialect, "orders"),
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.UPDATE],
            function=Function(dummy_dialect, "capture_old_new"),
            referencing="OLD AS old_row NEW AS new_row",
        )
        sql, params = create_trigger.to_sql()

        assert "OLD AS old_row" in sql
        assert "NEW AS new_row" in sql


class TestDropTriggerStatements:
    """Tests for DROP TRIGGER statements."""

    def test_basic_drop_trigger(self, dummy_dialect: DummyDialect):
        """Tests basic DROP TRIGGER."""
        drop_trigger = DropTriggerExpression(dummy_dialect, trigger=Trigger(dummy_dialect, "old_trigger"), table=Table(dummy_dialect, "users"))
        sql, params = drop_trigger.to_sql()

        assert sql == 'DROP TRIGGER "old_trigger" ON "users"'
        assert params == ()

    def test_drop_trigger_without_table(self, dummy_dialect: DummyDialect):
        """Tests DROP TRIGGER without table name."""
        drop_trigger = DropTriggerExpression(dummy_dialect, trigger=Trigger(dummy_dialect, "old_trigger"))
        sql, params = drop_trigger.to_sql()

        assert sql == 'DROP TRIGGER "old_trigger"'
        assert params == ()

    def test_drop_trigger_if_exists(self, dummy_dialect: DummyDialect):
        """Tests DROP TRIGGER IF EXISTS."""
        drop_trigger = DropTriggerExpression(
            dummy_dialect, trigger=Trigger(dummy_dialect, "maybe_exists"), table=Table(dummy_dialect, "users"), if_exists=True
        )
        sql, params = drop_trigger.to_sql()

        assert "IF EXISTS" in sql
        assert '"maybe_exists"' in sql

    def test_drop_trigger_if_exists_without_table(self, dummy_dialect: DummyDialect):
        """Tests DROP TRIGGER IF EXISTS without table name."""
        drop_trigger = DropTriggerExpression(dummy_dialect, trigger=Trigger(dummy_dialect, "maybe_exists"), if_exists=True)
        sql, params = drop_trigger.to_sql()

        assert "IF EXISTS" in sql
