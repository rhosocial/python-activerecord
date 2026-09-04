# tests/rhosocial/activerecord_test/feature/backend/introspection/test_introspection_triggers_async.py
"""Async twin of test_introspection_triggers.py for SQLite trigger introspection."""

import pytest

from rhosocial.activerecord.backend.introspection.types import (
    TriggerInfo,
)


class TestAsyncListTriggers:
    """Tests for list_triggers method."""

    @pytest.mark.asyncio
    async def test_list_triggers_empty_database(self, async_sqlite_memory_backend):
        """Test list_triggers on database without triggers."""
        triggers = await async_sqlite_memory_backend.introspector.list_triggers()

        assert isinstance(triggers, list)
        assert len(triggers) == 0

    @pytest.mark.asyncio
    async def test_list_triggers_with_trigger(self, async_backend_with_trigger):
        """Test list_triggers returns created triggers."""
        triggers = await async_backend_with_trigger.introspector.list_triggers()

        trigger_names = [t.name for t in triggers]
        assert "update_user_timestamp" in trigger_names

    @pytest.mark.asyncio
    async def test_list_triggers_returns_trigger_info(self, async_backend_with_trigger):
        """Test that list_triggers returns TriggerInfo objects."""
        triggers = await async_backend_with_trigger.introspector.list_triggers()

        for trigger in triggers:
            assert isinstance(trigger, TriggerInfo)

    @pytest.mark.asyncio
    async def test_list_triggers_schema(self, async_backend_with_trigger):
        """Test that schema is correctly set."""
        triggers = await async_backend_with_trigger.introspector.list_triggers()

        for trigger in triggers:
            assert trigger.schema == "main"

    @pytest.mark.asyncio
    async def test_list_triggers_caching(self, async_backend_with_trigger):
        """Test that trigger list is cached."""
        triggers1 = await async_backend_with_trigger.introspector.list_triggers()
        triggers2 = await async_backend_with_trigger.introspector.list_triggers()

        assert triggers1 is triggers2

    @pytest.mark.asyncio
    async def test_list_triggers_filter_by_table(self, async_backend_with_trigger):
        """Test filtering triggers by table."""
        triggers = await async_backend_with_trigger.introspector.list_triggers(table="users")

        for trigger in triggers:
            assert trigger.table_name == "users"

    @pytest.mark.asyncio
    async def test_list_triggers_filter_by_other_table(self, async_backend_with_trigger):
        """Test filtering triggers by table without triggers."""
        triggers = await async_backend_with_trigger.introspector.list_triggers(table="posts")

        assert len(triggers) == 0


class TestAsyncGetTriggerInfo:
    """Tests for get_trigger_info method."""

    @pytest.mark.asyncio
    async def test_get_trigger_info_existing(self, async_backend_with_trigger):
        """Test get_trigger_info for existing trigger."""
        trigger = await async_backend_with_trigger.introspector.get_trigger_info("update_user_timestamp")

        assert trigger is not None
        assert isinstance(trigger, TriggerInfo)
        assert trigger.name == "update_user_timestamp"

    @pytest.mark.asyncio
    async def test_get_trigger_info_nonexistent(self, async_sqlite_memory_backend):
        """Test get_trigger_info for non-existent trigger."""
        trigger = await async_sqlite_memory_backend.introspector.get_trigger_info("nonexistent")

        assert trigger is None

    @pytest.mark.asyncio
    async def test_get_trigger_info_table_name(self, async_backend_with_trigger):
        """Test that table_name is correctly set."""
        trigger = await async_backend_with_trigger.introspector.get_trigger_info("update_user_timestamp")

        assert trigger is not None
        assert trigger.table_name == "users"

    @pytest.mark.asyncio
    async def test_get_trigger_info_definition(self, async_backend_with_trigger):
        """Test that trigger definition is returned."""
        trigger = await async_backend_with_trigger.introspector.get_trigger_info("update_user_timestamp")

        assert trigger is not None
        assert trigger.definition is not None
        assert "TRIGGER" in trigger.definition.upper()


class TestAsyncTriggerDetails:
    """Tests for detailed trigger information."""

    @pytest.mark.asyncio
    async def test_multiple_triggers(self, async_sqlite_memory_backend):
        """Test multiple triggers on same table."""
        await async_sqlite_memory_backend.executescript("""
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

        triggers = await async_sqlite_memory_backend.introspector.list_triggers()

        trigger_names = {t.name for t in triggers}
        assert "trigger_insert" in trigger_names
        assert "trigger_update" in trigger_names
        assert "trigger_delete" in trigger_names

    @pytest.mark.asyncio
    async def test_trigger_timing(self, async_backend_with_trigger):
        """Test trigger timing detection."""
        trigger = await async_backend_with_trigger.introspector.get_trigger_info("update_user_timestamp")

        assert trigger is not None
        if trigger.timing:
            assert trigger.timing.upper() in ("AFTER", "BEFORE", "INSTEAD OF")
        else:
            assert trigger.definition is not None

    @pytest.mark.asyncio
    async def test_trigger_events(self, async_backend_with_trigger):
        """Test trigger events detection."""
        trigger = await async_backend_with_trigger.introspector.get_trigger_info("update_user_timestamp")

        assert trigger is not None
        if trigger.events:
            assert "UPDATE" in [e.upper() for e in trigger.events]
        else:
            assert trigger.definition is not None
            assert "UPDATE" in trigger.definition.upper()

    @pytest.mark.asyncio
    async def test_trigger_level(self, async_backend_with_trigger):
        """Test trigger level detection."""
        trigger = await async_backend_with_trigger.introspector.get_trigger_info("update_user_timestamp")

        assert trigger is not None
        assert trigger.level.upper() in ("ROW", "STATEMENT")

    @pytest.mark.asyncio
    async def test_before_insert_trigger(self, async_sqlite_memory_backend):
        """Test BEFORE INSERT trigger."""
        await async_sqlite_memory_backend.executescript("""
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

        trigger = await async_sqlite_memory_backend.introspector.get_trigger_info("validate_before_insert")

        assert trigger is not None
        assert trigger.definition is not None
        assert "BEFORE" in trigger.definition.upper()

    @pytest.mark.asyncio
    async def test_instead_of_trigger(self, async_sqlite_memory_backend):
        """Test INSTEAD OF trigger on view."""
        await async_sqlite_memory_backend.executescript("""
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

        trigger = await async_sqlite_memory_backend.introspector.get_trigger_info("instead_of_insert")

        assert trigger is not None
        assert trigger.definition is not None
        assert "INSTEAD OF" in trigger.definition.upper()

    @pytest.mark.asyncio
    async def test_trigger_with_condition(self, async_sqlite_memory_backend):
        """Test trigger with WHEN condition."""
        await async_sqlite_memory_backend.executescript("""
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

        trigger = await async_sqlite_memory_backend.introspector.get_trigger_info("conditional_trigger")

        assert trigger is not None
        assert trigger.definition is not None
