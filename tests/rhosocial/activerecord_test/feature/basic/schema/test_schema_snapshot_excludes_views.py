# tests/rhosocial/activerecord_test/feature/basic/schema/test_schema_snapshot_excludes_views.py
"""A schema snapshot models tables, not views.

``list_tables`` returns views alongside tables -- a view *is* a relation the
catalog knows about -- but a view carries none of what ``SchemaSnapshot``
records: no constraints, no indexes, no foreign keys, and no row-level
guarantee. Admitting one produced diff noise on every run, an ERD that drew
views as if they were tables, and a phantom DROP for an object no migration had
ever created.

A materialized view is excluded for the same reason and additionally because it
holds a snapshot, which is not schema.
"""


import pytest

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.introspection.types import TableType
from rhosocial.activerecord.backend.schema.differ import SchemaDiffer
from rhosocial.activerecord.backend.schema.snapshot import (
    SyncSchemaSnapshotBuilder,
    is_relation_table,
)

DDL = [
    "CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL)",
    "CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, total REAL)",
    "CREATE VIEW order_totals AS "
    "SELECT customer_id, SUM(total) AS total FROM orders GROUP BY customer_id",
    "CREATE VIEW rich_customers AS SELECT * FROM customers WHERE name LIKE 'A%'",
]


@pytest.fixture
def snapshot_db():
    """A SQLite database holding two tables and two views."""
    backend = SQLiteBackend(SQLiteConnectionConfig(database=":memory:"))
    backend.connect()
    backend.introspect_and_adapt()
    cursor = backend.connection.cursor()
    for statement in DDL:
        cursor.execute(statement)
    backend.connection.commit()
    yield backend
    backend.disconnect()


@pytest.fixture
def snapshots(snapshot_db):
    """Two snapshots of the same database, for diffing."""
    introspector = snapshot_db.introspector
    builder = SyncSchemaSnapshotBuilder(introspector, snapshot_db.dialect)
    return builder.build(), builder.build()


class TestTableTypeMembers:
    def test_materialized_view_is_a_member(self):
        """SQLite has none, but the enum is shared across backends."""
        assert "MATERIALIZED_VIEW" in {member.name for member in TableType}

    def test_object_declaration_is_a_separate_enum(self):
        """Intent and observation are kept apart on purpose."""
        from rhosocial.activerecord.base import ObjectDeclaration

        assert ObjectDeclaration is not TableType


class TestIsRelationTable:
    @pytest.mark.parametrize(
        "table_type, expected",
        [
            (TableType.BASE_TABLE, True),
            (TableType.SYSTEM_TABLE, True),
            (TableType.TEMPORARY, True),
            (TableType.EXTERNAL, True),
            (TableType.VIEW, False),
            (TableType.MATERIALIZED_VIEW, False),
            (None, True),
        ],
    )
    def test_classification(self, table_type, expected):
        assert is_relation_table(table_type) is expected


class TestSnapshotExcludesViews:
    def test_views_are_introspectable(self, snapshot_db):
        """The exclusion is the snapshot's choice, not introspection's."""
        introspector = snapshot_db.introspector
        names = {t.name for t in introspector.list_tables()}
        types = {t.name: t.table_type for t in introspector.list_tables()}
        assert {"order_totals", "rich_customers"} <= names
        assert types["order_totals"] == TableType.VIEW
        assert types["customers"] == TableType.BASE_TABLE

    def test_tables_are_captured(self, snapshots):
        old, _ = snapshots
        assert "customers" in old.tables
        assert "orders" in old.tables

    def test_views_are_not_captured(self, snapshots):
        old, _ = snapshots
        assert "order_totals" not in old.tables
        assert "rich_customers" not in old.tables

    def test_no_phantom_drops_for_views(self, snapshots):
        """The failure this fixes: a diff reporting objects nobody created."""
        old, new = snapshots
        diff = SchemaDiffer().compare(old, new)
        assert diff.removed_tables == []
        assert diff.added_tables == []

    def test_a_view_added_later_does_not_appear_as_a_new_table(self, snapshot_db):
        introspector = snapshot_db.introspector
        builder = SyncSchemaSnapshotBuilder(introspector, snapshot_db.dialect)
        before = builder.build()

        cursor = snapshot_db.connection.cursor()
        cursor.execute("CREATE VIEW late_view AS SELECT id FROM customers")
        snapshot_db.connection.commit()

        after = builder.build()
        diff = SchemaDiffer().compare(before, after)

        assert "late_view" not in diff.added_tables
        assert diff.added_tables == []


class TestRealTablesStillDiffer:
    """The exclusion must not blunt the diff for actual tables."""

    def test_a_new_table_is_still_reported(self, snapshots, snapshot_db):
        old, _ = snapshots
        cursor = snapshot_db.connection.cursor()
        cursor.execute("CREATE TABLE later (id INTEGER PRIMARY KEY, note TEXT)")
        snapshot_db.connection.commit()

        introspector = snapshot_db.introspector
        new = SyncSchemaSnapshotBuilder(introspector, snapshot_db.dialect).build()
        diff = SchemaDiffer().compare(old, new)

        assert diff.added_tables == ["later"]
