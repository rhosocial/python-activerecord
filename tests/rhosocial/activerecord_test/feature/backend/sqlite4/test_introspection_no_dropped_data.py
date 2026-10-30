# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_introspection_no_dropped_data.py
"""The introspector must not throw away what the database already told it.

A review compared four CLIs over one database and found fields the library
computed and the CLI never showed. Most of that was the CLI's own projection
and is fixed elsewhere; these are the cases where the *library* had the value
and dropped it, or asked the engine a question and ignored the answer:

* a view's definition -- the SELECT read ``sqlite_master`` without the ``sql``
  column, so every view reported ``definition=None``;
* a column's uniqueness -- SQLite records it on the index, so reporting
  ``False`` for a column under a unique index asserted something untrue;
* a trigger's timing and events -- present in the DDL, left empty;
* the database's encoding, size and table count -- three pragmas away, left
  ``None``.

Each test below creates the shape it needs rather than relying on a shared
fixture, so a failure names the field that regressed.
"""

import pytest

from rhosocial.activerecord.backend.introspection.types import IntrospectionScope


@pytest.fixture
def probe_db(sqlite_backend):
    """A database with the shapes these five answers depend on."""
    b = sqlite_backend
    b.introspector.clear_cache()
    b.executescript(
        """
        DROP TABLE IF EXISTS arx_posts;
        DROP TABLE IF EXISTS arx_users;
        DROP TABLE IF EXISTS arx_metrics;
        DROP VIEW IF EXISTS arx_active;
        DROP TRIGGER IF EXISTS arx_ai;

        CREATE TABLE arx_users (
            id INTEGER PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            name TEXT NOT NULL
        );
        CREATE TABLE arx_posts (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL
                REFERENCES arx_users(id) ON DELETE CASCADE,
            title TEXT NOT NULL
        );
        CREATE TABLE arx_metrics (
            id INTEGER PRIMARY KEY,
            width INTEGER, height INTEGER,
            area INTEGER GENERATED ALWAYS AS (width * height) STORED
        );

        CREATE INDEX arx_posts_title ON arx_posts(title)
            WHERE title IS NOT NULL;
        CREATE INDEX arx_posts_user_desc ON arx_posts(user_id DESC);

        CREATE VIEW arx_active AS
            SELECT id, email FROM arx_users WHERE id > 0;

        CREATE TRIGGER arx_ai AFTER INSERT ON arx_posts
        BEGIN
            UPDATE arx_users SET name = name WHERE id = NEW.user_id;
        END;
        """
    )
    yield b
    b.introspector.clear_cache()
    b.executescript(
        """
        DROP TRIGGER IF EXISTS arx_ai;
        DROP VIEW IF EXISTS arx_active;
        DROP TABLE IF EXISTS arx_metrics;
        DROP TABLE IF EXISTS arx_posts;
        DROP TABLE IF EXISTS arx_users;
        """
    )
    b.introspector.clear_cache()


class TestViewDefinition:
    def test_definition_comes_back(self, probe_db):
        """``SELECT name`` alone cannot answer what a view is made of."""
        views = probe_db.introspector.list_views()
        view = next(v for v in views if v.name == "arx_active")

        assert view.definition is not None
        assert "SELECT" in view.definition.upper()
        assert "arx_users" in view.definition


class TestColumnUniqueness:
    def test_unique_column_is_reported_unique(self, probe_db):
        """``email`` is under a UNIQUE index; the flag must say so.

        SQLite keeps uniqueness on the index, not on the column, so a parser
        that only reads the column row reports ``False`` for every column --
        which is a wrong answer, not a missing one, because a caller building
        a model from it would drop the constraint.
        """
        columns = probe_db.introspector.list_columns("arx_users")
        by_name = {c.name: c for c in columns}

        assert by_name["email"].is_unique is True
        assert by_name["name"].is_unique is False
        # A primary key is unique by definition, and the row says nothing
        # about it.
        assert by_name["id"].is_unique is True

    def test_partial_unique_index_does_not_make_a_column_unique(self, probe_db):
        """A partial index constrains only some rows, so it is not a promise.

        ``arx_posts_title`` has a WHERE clause; asserting uniqueness from it
        would claim more than the schema does.
        """
        probe_db.introspector.clear_cache()
        probe_db.executescript(
            "CREATE UNIQUE INDEX arx_posts_partial ON arx_posts(title) "
            "WHERE title <> ''"
        )
        try:
            columns = probe_db.introspector.list_columns("arx_posts")
            by_name = {c.name: c for c in columns}
            assert by_name["title"].is_unique is False
        finally:
            probe_db.executescript("DROP INDEX arx_posts_partial")


class TestTriggerTimingAndEvents:
    def test_timing_and_events_come_from_the_ddl(self, probe_db):
        """The header is only in the DDL; parsing it beats leaving blanks."""
        triggers = probe_db.introspector.list_triggers()
        trigger = next(t for t in triggers if t.name == "arx_ai")

        assert trigger.timing == "AFTER"
        assert trigger.events == ["INSERT"]

    def test_before_delete_is_read(self, probe_db):
        """A second header, so the parser is not matching one spelling."""
        probe_db.introspector.clear_cache()
        probe_db.executescript(
            "CREATE TRIGGER arx_bd BEFORE DELETE ON arx_posts "
            "BEGIN SELECT 1; END"
        )
        try:
            triggers = probe_db.introspector.list_triggers()
            trigger = next(t for t in triggers if t.name == "arx_bd")
            assert trigger.timing == "BEFORE"
            assert trigger.events == ["DELETE"]
        finally:
            probe_db.executescript("DROP TRIGGER arx_bd")


class TestDatabaseFacts:
    def test_encoding_size_and_table_count_are_answered(self, probe_db):
        """Three pragmas and a count, none of which needs a second round trip.

        Leaving them ``None`` is the same as not asking, and each is one
        ``PRAGMA`` away.
        """
        info = probe_db.introspector.get_database_info()

        assert info.encoding is not None
        assert info.size_bytes is not None and info.size_bytes > 0
        # Tables only: the view and the trigger this fixture creates are not
        # tables, and counting them would inflate the answer.
        assert info.table_count is not None and info.table_count >= 3

    def test_size_is_pages_times_page_size(self, probe_db):
        """The number is derived, so check the derivation, not just presence."""
        info = probe_db.introspector.get_database_info()
        pages = probe_db.introspector.pragma.get("page_count")
        page_size = probe_db.introspector.pragma.get("page_size")

        assert int(pages["page_count"]) * int(page_size["page_size"]) == info.size_bytes


class TestCacheStillSeparatesTheFamilies:
    def test_columns_and_database_info_do_not_share_a_key(self, probe_db):
        """The two new answers live under different scopes.

        The database facts and the column list are different questions, and one
        cache key would make one answer the other's question. The cache's own
        length is the observable: two distinct entries, not one reused.
        """
        introspector = probe_db.introspector
        introspector.clear_cache()

        introspector.get_database_info()
        introspector.list_columns("arx_users")

        assert len(introspector._cache) == 2

        db_key = introspector._cache.key(IntrospectionScope.DATABASE)
        col_key = introspector._cache.key(IntrospectionScope.COLUMN, "arx_users")
        assert db_key != col_key
        assert introspector._cache.get(db_key) is not None
        assert introspector._cache.get(col_key) is not None
