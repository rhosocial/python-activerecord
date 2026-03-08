# tests/rhosocial/activerecord_test/feature/backend/dummy/test_trigger_mixin.py
"""Tests for TriggerMixin format methods."""
import pytest
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression import Column, Literal


class TestTriggerMixinFormatMethods:
    """Tests for TriggerMixin format_create/drop_trigger_statement methods."""

    def test_format_create_trigger_basic(self, dummy_dialect: DummyDialect):
        """Tests format_create_trigger_statement basic case."""
        from rhosocial.activerecord.backend.expression.statements import (
            CreateTriggerExpression, TriggerTiming, TriggerEvent, TriggerLevel
        )

        create_trigger = CreateTriggerExpression(
            dummy_dialect,
            trigger_name="audit_trigger",
            table_name="users",
            timing=TriggerTiming.AFTER,
            events=[TriggerEvent.INSERT],
            function_name="log_audit"
        )
        sql, params = dummy_dialect.format_create_trigger_statement(create_trigger)

        assert 'CREATE TRIGGER' in sql
        assert '"audit_trigger"' in sql
        assert 'AFTER' in sql
        assert 'INSERT' in sql
        assert 'ON' in sql
        assert '"users"' in sql
        assert 'FOR EACH ROW' in sql
        assert 'EXECUTE' in sql
        assert '"log_audit"' in sql
        assert params == ()

    def test_format_create_trigger_with_condition(self, dummy_dialect: DummyDialect):
        """Tests format_create_trigger_statement with WHEN condition."""
        from rhosocial.activerecord.backend.expression.statements import (
            CreateTriggerExpression, TriggerTiming, TriggerEvent, TriggerLevel
        )

        condition = Column(dummy_dialect, "status") == Literal(dummy_dialect, "active")
        create_trigger = CreateTriggerExpression(
            dummy_dialect,
            trigger_name="status_trigger",
            table_name="orders",
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.UPDATE],
            function_name="validate_status",
            condition=condition
        )
        sql, params = dummy_dialect.format_create_trigger_statement(create_trigger)

        assert 'WHEN' in sql
        assert '"status" = ?' in sql
        assert params == ("active",)

    def test_format_create_trigger_statement_level(self, dummy_dialect: DummyDialect):
        """Tests format_create_trigger_statement with FOR EACH STATEMENT."""
        from rhosocial.activerecord.backend.expression.statements import (
            CreateTriggerExpression, TriggerTiming, TriggerEvent, TriggerLevel
        )

        create_trigger = CreateTriggerExpression(
            dummy_dialect,
            trigger_name="bulk_trigger",
            table_name="logs",
            timing=TriggerTiming.AFTER,
            events=[TriggerEvent.INSERT],
            function_name="process_bulk",
            level=TriggerLevel.STATEMENT
        )
        sql, params = dummy_dialect.format_create_trigger_statement(create_trigger)

        assert 'FOR EACH STATEMENT' in sql
        assert params == ()

    def test_format_create_trigger_with_referencing(self, dummy_dialect: DummyDialect):
        """Tests format_create_trigger_statement with REFERENCING clause."""
        from rhosocial.activerecord.backend.expression.statements import (
            CreateTriggerExpression, TriggerTiming, TriggerEvent
        )

        create_trigger = CreateTriggerExpression(
            dummy_dialect,
            trigger_name="ref_trigger",
            table_name="audit_log",
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.UPDATE],
            function_name="capture_changes",
            referencing="OLD AS old_row NEW AS new_row"
        )
        sql, params = dummy_dialect.format_create_trigger_statement(create_trigger)

        assert 'OLD AS old_row' in sql
        assert 'NEW AS new_row' in sql
        assert params == ()

    def test_format_create_trigger_if_not_exists(self, dummy_dialect: DummyDialect):
        """Tests format_create_trigger_statement with IF NOT EXISTS."""
        from rhosocial.activerecord.backend.expression.statements import (
            CreateTriggerExpression, TriggerTiming, TriggerEvent
        )

        create_trigger = CreateTriggerExpression(
            dummy_dialect,
            trigger_name="safe_trigger",
            table_name="data",
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.INSERT],
            function_name="validate_data",
            if_not_exists=True
        )
        sql, params = dummy_dialect.format_create_trigger_statement(create_trigger)

        assert 'IF NOT EXISTS' in sql
        assert params == ()

    def test_format_create_trigger_update_of_columns(self, dummy_dialect: DummyDialect):
        """Tests format_create_trigger_statement with UPDATE OF columns."""
        from rhosocial.activerecord.backend.expression.statements import (
            CreateTriggerExpression, TriggerTiming, TriggerEvent
        )

        create_trigger = CreateTriggerExpression(
            dummy_dialect,
            trigger_name="col_trigger",
            table_name="products",
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.UPDATE],
            update_columns=["price", "quantity"],
            function_name="check_changes"
        )
        sql, params = dummy_dialect.format_create_trigger_statement(create_trigger)

        assert 'UPDATE OF' in sql
        assert '"price"' in sql
        assert '"quantity"' in sql
        assert params == ()

    def test_format_drop_trigger_basic(self, dummy_dialect: DummyDialect):
        """Tests format_drop_trigger_statement basic case."""
        from rhosocial.activerecord.backend.expression.statements import DropTriggerExpression

        drop_trigger = DropTriggerExpression(
            dummy_dialect,
            trigger_name="old_trigger",
            table_name="users"
        )
        sql, params = dummy_dialect.format_drop_trigger_statement(drop_trigger)

        assert 'DROP TRIGGER' in sql
        assert '"old_trigger"' in sql
        assert 'ON' in sql
        assert '"users"' in sql
        assert params == ()

    def test_format_drop_trigger_if_exists(self, dummy_dialect: DummyDialect):
        """Tests format_drop_trigger_statement with IF EXISTS."""
        from rhosocial.activerecord.backend.expression.statements import DropTriggerExpression

        drop_trigger = DropTriggerExpression(
            dummy_dialect,
            trigger_name="maybe_trigger",
            table_name="temp",
            if_exists=True
        )
        sql, params = dummy_dialect.format_drop_trigger_statement(drop_trigger)

        assert 'IF EXISTS' in sql
        assert '"maybe_trigger"' in sql
        assert params == ()

    def test_format_drop_trigger_without_table(self, dummy_dialect: DummyDialect):
        """Tests format_drop_trigger_statement without table name."""
        from rhosocial.activerecord.backend.expression.statements import DropTriggerExpression

        drop_trigger = DropTriggerExpression(
            dummy_dialect,
            trigger_name="standalone_trigger"
        )
        sql, params = dummy_dialect.format_drop_trigger_statement(drop_trigger)

        assert 'DROP TRIGGER' in sql
        assert '"standalone_trigger"' in sql
        assert 'ON' not in sql
        assert params == ()
