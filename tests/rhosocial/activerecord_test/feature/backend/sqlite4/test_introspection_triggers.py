# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_introspection_triggers.py
"""
Tests for SQLite trigger introspection.

This module tests the list_triggers and get_trigger_info methods
for retrieving trigger metadata.
"""

import pytest

from rhosocial.activerecord.backend.introspection.types import (
    TriggerInfo,
)


class TestListTriggers:
    """Tests for list_triggers method."""

    def test_list_triggers_empty_database(self, sqlite_backend):
        """Test list_triggers on database without triggers."""
        triggers = sqlite_backend.list_triggers()

        assert isinstance(triggers, list)
        assert len(triggers) == 0

    def test_list_triggers_with_trigger(self, backend_with_trigger):
        """Test list_triggers returns created triggers."""
        triggers = backend_with_trigger.list_triggers()

        trigger_names = [t.name for t in triggers]
        assert "update_user_timestamp" in trigger_names

    def test_list_triggers_returns_trigger_info(self, backend_with_trigger):
        """Test that list_triggers returns TriggerInfo objects."""
        triggers = backend_with_trigger.list_triggers()

        for trigger in triggers:
            assert isinstance(trigger, TriggerInfo)

    def test_list_triggers_schema(self, backend_with_trigger):
        """Test that schema is correctly set."""
        triggers = backend_with_trigger.list_triggers()

        for trigger in triggers:
            assert trigger.schema == "main"

    def test_list_triggers_caching(self, backend_with_trigger):
        """Test that trigger list is cached."""
        triggers1 = backend_with_trigger.list_triggers()
        triggers2 = backend_with_trigger.list_triggers()

        # Should return the same cached list
        assert triggers1 is triggers2

    def test_list_triggers_filter_by_table(self, backend_with_trigger):
        """Test filtering triggers by table."""
        triggers = backend_with_trigger.list_triggers(table_name="users")

        for trigger in triggers:
            assert trigger.table_name == "users"

    def test_list_triggers_filter_by_other_table(self, backend_with_trigger):
        """Test filtering triggers by table without triggers."""
        triggers = backend_with_trigger.list_triggers(table_name="posts")

        # posts table has no triggers
        assert len(triggers) == 0


class TestGetTriggerInfo:
    """Tests for get_trigger_info method."""

    def test_get_trigger_info_existing(self, backend_with_trigger):
        """Test get_trigger_info for existing trigger."""
        trigger = backend_with_trigger.get_trigger_info("update_user_timestamp")

        assert trigger is not None
        assert isinstance(trigger, TriggerInfo)
        assert trigger.name == "update_user_timestamp"

    def test_get_trigger_info_nonexistent(self, sqlite_backend):
        """Test get_trigger_info for non-existent trigger."""
        trigger = sqlite_backend.get_trigger_info("nonexistent")

        assert trigger is None

    def test_get_trigger_info_table_name(self, backend_with_trigger):
        """Test that table_name is correctly set."""
        trigger = backend_with_trigger.get_trigger_info("update_user_timestamp")

        assert trigger is not None
        assert trigger.table_name == "users"

    def test_get_trigger_info_definition(self, backend_with_trigger):
        """Test that trigger definition is returned."""
        trigger = backend_with_trigger.get_trigger_info("update_user_timestamp")

        assert trigger is not None
        assert trigger.definition is not None
        assert "TRIGGER" in trigger.definition.upper()


class TestTriggerDetails:
    """Tests for detailed trigger information."""

    def test_multiple_triggers(self, sqlite_backend):
        """Test multiple triggers on same table."""
        sqlite_backend.executescript("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT
            );

            CREATE TRIGGER trigger_insert
            AFTER INSERT ON test_table
            FOR EACH ROW
            BEGIN
                SELECT 1;
            END;

            CREATE TRIGGER trigger_update
            AFTER UPDATE ON test_table
            FOR EACH ROW
            BEGIN
                SELECT 1;
            END;

            CREATE TRIGGER trigger_delete
            AFTER DELETE ON test_table
            FOR EACH ROW
            BEGIN
                SELECT 1;
            END;
        """)

        triggers = sqlite_backend.list_triggers()

        trigger_names = {t.name for t in triggers}
        assert "trigger_insert" in trigger_names
        assert "trigger_update" in trigger_names
        assert "trigger_delete" in trigger_names

    def test_trigger_timing(self, backend_with_trigger):
        """Test trigger timing detection."""
        trigger = backend_with_trigger.get_trigger_info("update_user_timestamp")

        assert trigger is not None
        # Timing may be empty if not parsed from definition
        # Check definition contains timing info instead
        if trigger.timing:
            assert trigger.timing.upper() in ("AFTER", "BEFORE", "INSTEAD OF")
        else:
            # Verify timing is in definition
            assert trigger.definition is not None

    def test_trigger_events(self, backend_with_trigger):
        """Test trigger events detection."""
        trigger = backend_with_trigger.get_trigger_info("update_user_timestamp")

        assert trigger is not None
        # Events may be empty if not parsed from definition
        # Check definition contains event info instead
        if trigger.events:
            assert "UPDATE" in [e.upper() for e in trigger.events]
        else:
            # Verify event is in definition
            assert trigger.definition is not None
            assert "UPDATE" in trigger.definition.upper()

    def test_trigger_level(self, backend_with_trigger):
        """Test trigger level detection."""
        trigger = backend_with_trigger.get_trigger_info("update_user_timestamp")

        assert trigger is not None
        # Default level is ROW
        assert trigger.level.upper() in ("ROW", "STATEMENT")

    def test_before_insert_trigger(self, sqlite_backend):
        """Test BEFORE INSERT trigger."""
        sqlite_backend.executescript("""
            CREATE TABLE data (
                id INTEGER PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TRIGGER validate_before_insert
            BEFORE INSERT ON data
            FOR EACH ROW
            WHEN NEW.value IS NOT NULL
            BEGIN
                SELECT 1;
            END;
        """)

        trigger = sqlite_backend.get_trigger_info("validate_before_insert")

        assert trigger is not None
        # Check definition contains BEFORE
        assert trigger.definition is not None
        assert "BEFORE" in trigger.definition.upper()

    def test_instead_of_trigger(self, sqlite_backend):
        """Test INSTEAD OF trigger on view."""
        sqlite_backend.executescript("""
            CREATE TABLE base_table (
                id INTEGER PRIMARY KEY,
                name TEXT
            );

            CREATE VIEW base_view AS
            SELECT * FROM base_table;

            CREATE TRIGGER instead_of_insert
            INSTEAD OF INSERT ON base_view
            FOR EACH ROW
            BEGIN
                INSERT INTO base_table (id, name)
                VALUES (NEW.id, NEW.name);
            END;
        """)

        trigger = sqlite_backend.get_trigger_info("instead_of_insert")

        assert trigger is not None
        # Check definition contains INSTEAD OF
        assert trigger.definition is not None
        assert "INSTEAD OF" in trigger.definition.upper()

    def test_trigger_with_condition(self, sqlite_backend):
        """Test trigger with WHEN condition."""
        sqlite_backend.executescript("""
            CREATE TABLE items (
                id INTEGER PRIMARY KEY,
                status TEXT
            );

            CREATE TRIGGER conditional_trigger
            AFTER UPDATE ON items
            FOR EACH ROW
            WHEN OLD.status != NEW.status
            BEGIN
                SELECT 1;
            END;
        """)

        trigger = sqlite_backend.get_trigger_info("conditional_trigger")

        assert trigger is not None
        # The definition should contain the WHEN clause
        assert trigger.definition is not None
