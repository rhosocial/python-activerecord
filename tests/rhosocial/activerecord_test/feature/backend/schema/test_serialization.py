# tests/rhosocial/activerecord_test/feature/backend/schema/test_serialization.py
"""Tests for schema snapshot serialisation (P4) and key differ logic (P1/P2)."""

from __future__ import annotations

import json

import pytest

from rhosocial.activerecord.backend.schema import (
    SchemaSnapshot,
    SchemaDiff,
    TableDiff,
    ColumnDiff,
    SchemaDiffer,
)
from rhosocial.activerecord.backend.schema.differ import SchemaDiffer
from rhosocial.activerecord.backend.expression.types import (
    IntegerType,
    VarCharType,
    ArrayType,
    BooleanType,
    DecimalType,
    SmallIntType,
)
from rhosocial.activerecord.backend.introspection.types import (
    DatabaseInfo,
    TableInfo,
    ColumnInfo,
    IndexInfo,
    IndexColumnInfo,
    ForeignKeyInfo,
    ColumnNullable,
    TableType,
    IndexType,
    ReferentialAction,
)
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# P4 — DataType serialisation
# ---------------------------------------------------------------------------


class TestDataTypeSerialization:
    def test_paramless_type(self):
        dt = IntegerType()
        d = dt.to_dict() if hasattr(dt, "to_dict") else None
        # Use internal helper
        from rhosocial.activerecord.backend.schema.snapshot import (
            _data_type_to_dict,
            _data_type_from_dict,
        )
        d = _data_type_to_dict(dt)
        restored = _data_type_from_dict(d)
        assert type(restored) is IntegerType

    def test_parameterised_type(self):
        from rhosocial.activerecord.backend.schema.snapshot import (
            _data_type_to_dict,
            _data_type_from_dict,
        )
        dt = VarCharType(length=255)
        restored = _data_type_from_dict(_data_type_to_dict(dt))
        assert restored.length == 255

    def test_nested_array_type(self):
        from rhosocial.activerecord.backend.schema.snapshot import (
            _data_type_to_dict,
            _data_type_from_dict,
        )
        dt = ArrayType(element_type=IntegerType(), dimensions=2)
        restored = _data_type_from_dict(_data_type_to_dict(dt))
        assert isinstance(restored.element_type, IntegerType)
        assert restored.dimensions == 2

    def test_decimal_type(self):
        from rhosocial.activerecord.backend.schema.snapshot import (
            _data_type_to_dict,
            _data_type_from_dict,
        )
        dt = DecimalType(precision=10, scale=2)
        restored = _data_type_from_dict(_data_type_to_dict(dt))
        assert restored.precision == 10
        assert restored.scale == 2


# ---------------------------------------------------------------------------
# P4 — SchemaSnapshot serialisation roundtrip
# ---------------------------------------------------------------------------


class TestSnapshotSerialization:
    @pytest.fixture
    def snapshot(self):
        db_info = DatabaseInfo(
            name="testdb",
            version="16.0",
            version_tuple=(16, 0, 0),
            vendor="postgresql",
        )
        col = ColumnInfo(
            name="id",
            table_name="users",
            schema="public",
            ordinal_position=1,
            data_type="INTEGER",
            parsed_data_type=IntegerType(),
            nullable=ColumnNullable.NOT_NULL,
            is_primary_key=True,
        )
        col2 = ColumnInfo(
            name="name",
            table_name="users",
            schema="public",
            ordinal_position=2,
            data_type="VARCHAR(255)",
            parsed_data_type=VarCharType(length=255),
            nullable=ColumnNullable.NULLABLE,
        )
        tbl = TableInfo(
            name="users",
            schema="public",
            columns=[col, col2],
            table_type=TableType.BASE_TABLE,
        )
        return SchemaSnapshot(
            dialect_class="test.TestDialect",
            captured_at=datetime(2026, 6, 20, 17, 0, 0, tzinfo=timezone.utc),
            database_info=db_info,
            tables={"users": tbl},
            schema_name="public",
        )

    def test_to_dict_has_keys(self, snapshot):
        d = snapshot.to_dict()
        assert "dialect_class" in d
        assert "captured_at" in d
        assert "database_info" in d
        assert "tables" in d

    def test_to_dict_column_structure(self, snapshot):
        d = snapshot.to_dict()
        col = d["tables"]["users"]["columns"][0]
        assert col["name"] == "id"
        assert col["data_type"] == "INTEGER"
        assert "parsed_data_type" in col
        assert col["parsed_data_type"]["type"].endswith("IntegerType")

    def test_full_roundtrip(self, snapshot):
        d = snapshot.to_dict()
        restored = SchemaSnapshot.from_dict(d)
        assert restored.dialect_class == snapshot.dialect_class
        assert restored.schema_name == snapshot.schema_name
        assert restored.database_info.name == "testdb"
        c = restored.tables["users"].columns[0]
        assert c.name == "id"
        assert isinstance(c.parsed_data_type, IntegerType)
        assert c.nullable == ColumnNullable.NOT_NULL
        assert c.is_primary_key is True

    def test_json_roundtrip(self, snapshot):
        d = snapshot.to_dict()
        json_str = json.dumps(d, ensure_ascii=False)
        d2 = json.loads(json_str)
        restored = SchemaSnapshot.from_dict(d2)
        c = restored.tables["users"].columns[0]
        assert c.name == "id"
        assert isinstance(c.parsed_data_type, IntegerType)
        assert c.nullable == ColumnNullable.NOT_NULL
        assert restored.tables["users"].table_type == TableType.BASE_TABLE


# ---------------------------------------------------------------------------
# P1 — Index content equivalence
# ---------------------------------------------------------------------------


class TestIndexEquivalence:
    def test_same_indexes(self):
        differ = SchemaDiffer()
        old_idx = IndexInfo(
            name="idx_name",
            table_name="users",
            is_unique=False,
            columns=[IndexColumnInfo("name")],
        )
        new_idx = IndexInfo(
            name="idx_name",
            table_name="users",
            is_unique=False,
            columns=[IndexColumnInfo("name")],
        )
        assert differ._indexes_equivalent(old_idx, new_idx)

    def test_unique_flag_change(self):
        differ = SchemaDiffer()
        old_idx = IndexInfo(
            name="idx_name", table_name="users", is_unique=False,
            columns=[IndexColumnInfo("name")],
        )
        new_idx = IndexInfo(
            name="idx_name", table_name="users", is_unique=True,
            columns=[IndexColumnInfo("name")],
        )
        assert not differ._indexes_equivalent(old_idx, new_idx)

    def test_column_list_change(self):
        differ = SchemaDiffer()
        old_idx = IndexInfo(
            name="idx_name", table_name="users",
            columns=[IndexColumnInfo("a"), IndexColumnInfo("b")],
        )
        new_idx = IndexInfo(
            name="idx_name", table_name="users",
            columns=[IndexColumnInfo("a")],  # b removed
        )
        assert not differ._indexes_equivalent(old_idx, new_idx)

    def test_column_order_change(self):
        differ = SchemaDiffer()
        old_idx = IndexInfo(
            name="idx_ab", table_name="users",
            columns=[IndexColumnInfo("a"), IndexColumnInfo("b")],
        )
        new_idx = IndexInfo(
            name="idx_ab", table_name="users",
            columns=[IndexColumnInfo("b"), IndexColumnInfo("a")],
        )
        assert not differ._indexes_equivalent(old_idx, new_idx)

    def test_index_type_change(self):
        from rhosocial.activerecord.backend.introspection.types import (
            IndexType,
        )
        differ = SchemaDiffer()
        old_idx = IndexInfo(
            name="idx", table_name="t",
            index_type=IndexType.BTREE,
            columns=[IndexColumnInfo("a")],
        )
        new_idx = IndexInfo(
            name="idx", table_name="t",
            index_type=IndexType.HASH,
            columns=[IndexColumnInfo("a")],
        )
        assert not differ._indexes_equivalent(old_idx, new_idx)


# ---------------------------------------------------------------------------
# P2 — Foreign key content equivalence
# ---------------------------------------------------------------------------


class TestFKEquivalence:
    def test_same_fk(self):
        differ = SchemaDiffer()
        old_fk = ForeignKeyInfo(
            name="fk_user",
            table_name="orders",
            columns=["user_id"],
            referenced_table="users",
            referenced_columns=["id"],
            on_delete=ReferentialAction.CASCADE,
        )
        new_fk = ForeignKeyInfo(
            name="fk_user",
            table_name="orders",
            columns=["user_id"],
            referenced_table="users",
            referenced_columns=["id"],
            on_delete=ReferentialAction.CASCADE,
        )
        assert differ._fk_equivalent(old_fk, new_fk)

    def test_referenced_table_change(self):
        differ = SchemaDiffer()
        old_fk = ForeignKeyInfo(
            name="fk_ref", table_name="t",
            columns=["x"], referenced_table="a",
            referenced_columns=["id"],
        )
        new_fk = ForeignKeyInfo(
            name="fk_ref", table_name="t",
            columns=["x"], referenced_table="b",
            referenced_columns=["id"],
        )
        assert not differ._fk_equivalent(old_fk, new_fk)

    def test_on_delete_change(self):
        differ = SchemaDiffer()
        old_fk = ForeignKeyInfo(
            name="fk", table_name="t", columns=["x"],
            referenced_table="a", referenced_columns=["id"],
            on_delete=ReferentialAction.CASCADE,
        )
        new_fk = ForeignKeyInfo(
            name="fk", table_name="t", columns=["x"],
            referenced_table="a", referenced_columns=["id"],
            on_delete=ReferentialAction.SET_NULL,
        )
        assert not differ._fk_equivalent(old_fk, new_fk)


# ---------------------------------------------------------------------------
# P1/P2 — _diff_table integration (same-name index/fk changes)
# ---------------------------------------------------------------------------


class TestDiffTableIntegration:
    def test_index_modification_detected(self):
        differ = SchemaDiffer()
        old_tbl = TableInfo(
            name="t",
            indexes=[
                IndexInfo(
                    name="idx_a", table_name="t", is_unique=False,
                    columns=[IndexColumnInfo("a")],
                ),
            ],
        )
        new_tbl = TableInfo(
            name="t",
            indexes=[
                IndexInfo(
                    name="idx_a", table_name="t", is_unique=True,
                    columns=[IndexColumnInfo("a")],
                ),
            ],
        )
        td = differ._diff_table("t", old_tbl, new_tbl)
        assert len(td.removed_indexes) == 1
        assert len(td.added_indexes) == 1

    def test_fk_modification_detected(self):
        differ = SchemaDiffer()
        old_tbl = TableInfo(
            name="t",
            foreign_keys=[
                ForeignKeyInfo(
                    name="fk", table_name="t",
                    columns=["x"], referenced_table="a",
                    referenced_columns=["id"],
                ),
            ],
        )
        new_tbl = TableInfo(
            name="t",
            foreign_keys=[
                ForeignKeyInfo(
                    name="fk", table_name="t",
                    columns=["x"], referenced_table="b",
                    referenced_columns=["id"],
                ),
            ],
        )
        td = differ._diff_table("t", old_tbl, new_tbl)
        assert len(td.removed_foreign_keys) == 1
        assert len(td.added_foreign_keys) == 1

    def test_unchanged_index_not_reported(self):
        differ = SchemaDiffer()
        old_tbl = TableInfo(
            name="t",
            indexes=[
                IndexInfo(
                    name="idx", table_name="t", is_unique=False,
                    columns=[IndexColumnInfo("a")],
                ),
            ],
        )
        new_tbl = TableInfo(
            name="t",
            indexes=[
                IndexInfo(
                    name="idx", table_name="t", is_unique=False,
                    columns=[IndexColumnInfo("a")],
                ),
            ],
        )
        td = differ._diff_table("t", old_tbl, new_tbl)
        assert len(td.removed_indexes) == 0
        assert len(td.added_indexes) == 0


# ---------------------------------------------------------------------------
# P3 — Roundtrip: snapshot → diff → result
# ---------------------------------------------------------------------------


class TestSnapshotDiffRoundtrip:
    """Build two similar snapshots, diff them, verify result."""

    @pytest.fixture
    def base_snapshot(self):
        db_info = DatabaseInfo(
            name="testdb", version="16.0", version_tuple=(16, 0, 0),
            vendor="postgresql",
        )
        cols = [
            ColumnInfo(
                name="id", table_name="users", schema="public",
                ordinal_position=1, data_type="INTEGER",
                parsed_data_type=IntegerType(),
                nullable=ColumnNullable.NOT_NULL,
                is_primary_key=True,
            ),
            ColumnInfo(
                name="name", table_name="users", schema="public",
                ordinal_position=2, data_type="VARCHAR(255)",
                parsed_data_type=VarCharType(length=255),
                nullable=ColumnNullable.NULLABLE,
            ),
        ]
        tbl = TableInfo(
            name="users", schema="public", columns=cols,
            table_type=TableType.BASE_TABLE,
        )
        return SchemaSnapshot(
            dialect_class="test.TestDialect",
            captured_at=datetime(2026, 6, 20, 17, 0, 0, tzinfo=timezone.utc),
            database_info=db_info,
            tables={"users": tbl},
            schema_name="public",
        )

    def test_identical_snapshots_produce_empty_diff(self, base_snapshot):
        differ = SchemaDiffer()
        diff = differ.compare(base_snapshot, base_snapshot)
        assert len(diff.removed_tables) == 0
        assert len(diff.added_tables) == 0
        assert len(diff.modified_tables) == 0

    def test_added_table(self, base_snapshot):
        db_info = base_snapshot.database_info
        new_tbl = TableInfo(
            name="posts", schema="public",
            columns=[
                ColumnInfo(
                    name="id", table_name="posts", schema="public",
                    ordinal_position=1, data_type="INTEGER",
                    parsed_data_type=IntegerType(),
                    nullable=ColumnNullable.NOT_NULL,
                ),
            ],
            table_type=TableType.BASE_TABLE,
        )
        new_snap = SchemaSnapshot(
            dialect_class=base_snapshot.dialect_class,
            captured_at=datetime(2026, 6, 20, 18, 0, 0, tzinfo=timezone.utc),
            database_info=db_info,
            tables={"users": base_snapshot.tables["users"], "posts": new_tbl},
            schema_name="public",
        )
        diff = SchemaDiffer().compare(base_snapshot, new_snap)
        assert diff.added_tables == ["posts"]
        assert len(diff.removed_tables) == 0
        assert len(diff.modified_tables) == 0

    def test_removed_table(self, base_snapshot):
        db_info = base_snapshot.database_info
        new_snap = SchemaSnapshot(
            dialect_class=base_snapshot.dialect_class,
            captured_at=datetime(2026, 6, 20, 18, 0, 0, tzinfo=timezone.utc),
            database_info=db_info,
            tables={},
            schema_name="public",
        )
        diff = SchemaDiffer().compare(base_snapshot, new_snap)
        assert diff.removed_tables == ["users"]
        assert len(diff.added_tables) == 0

    def test_added_column(self, base_snapshot):
        db_info = base_snapshot.database_info
        old_cols = base_snapshot.tables["users"].columns
        new_col = ColumnInfo(
            name="email", table_name="users", schema="public",
            ordinal_position=3, data_type="VARCHAR(255)",
            parsed_data_type=VarCharType(length=255),
            nullable=ColumnNullable.NULLABLE,
        )
        new_tbl = TableInfo(
            name="users", schema="public",
            columns=list(old_cols) + [new_col],
            table_type=TableType.BASE_TABLE,
        )
        new_snap = SchemaSnapshot(
            dialect_class=base_snapshot.dialect_class,
            captured_at=datetime(2026, 6, 20, 18, 0, 0, tzinfo=timezone.utc),
            database_info=db_info,
            tables={"users": new_tbl},
            schema_name="public",
        )
        diff = SchemaDiffer().compare(base_snapshot, new_snap)
        assert "users" in diff.modified_tables
        td = diff.table_diffs["users"]
        assert len(td.column_diffs) == 1
        assert td.column_diffs[0].column_name == "email"
        assert td.column_diffs[0].is_added

    def test_index_change(self, base_snapshot):
        db_info = base_snapshot.database_info
        old_tbl = base_snapshot.tables["users"]
        # Add an index to new snapshot
        idx = IndexInfo(
            name="idx_name", table_name="users", is_unique=False,
            columns=[IndexColumnInfo("name")],
        )
        new_tbl = TableInfo(
            name="users", schema="public",
            columns=old_tbl.columns,
            indexes=[idx],
            table_type=TableType.BASE_TABLE,
        )
        new_snap = SchemaSnapshot(
            dialect_class=base_snapshot.dialect_class,
            captured_at=datetime(2026, 6, 20, 18, 0, 0, tzinfo=timezone.utc),
            database_info=db_info,
            tables={"users": new_tbl},
            schema_name="public",
        )
        diff = SchemaDiffer().compare(base_snapshot, new_snap)
        td = diff.table_diffs["users"]
        assert len(td.added_indexes) == 1


# ---------------------------------------------------------------------------
# P3 — Real DB roundtrip: DDL → introspect → snapshot → diff
# ---------------------------------------------------------------------------


class TestRealDBRoundtrip:
    """Integration test: create real SQLite tables, build snapshots, diff.

    Covers the DDL → execute → introspect → snapshot → diff=empty path
    required by the design document.
    """

    @pytest.fixture
    def backend(self):
        from rhosocial.activerecord.backend.impl.sqlite.backend import (
            SQLiteBackend,
        )

        backend = SQLiteBackend(database=":memory:")
        backend.connect()
        backend.introspect_and_adapt()
        yield backend
        backend.disconnect()

    def build_snapshot(self, backend) -> SchemaSnapshot:
        from rhosocial.activerecord.backend.schema import (
            SyncSchemaSnapshotBuilder,
        )

        builder = SyncSchemaSnapshotBuilder(
            backend.introspector, backend.dialect
        )
        return builder.build(schema="main")

    def test_identical_snapshot_empty_diff(self, backend):
        """Same DB, two snapshots in sequence → no diff."""
        snap1 = self.build_snapshot(backend)
        snap2 = self.build_snapshot(backend)
        from rhosocial.activerecord.backend.impl.sqlite.schema.differ import (
            SQLiteSchemaDiffer,
        )

        diff = SQLiteSchemaDiffer().compare(snap1, snap2)
        assert diff.is_empty

    def test_added_table_detected(self, backend):
        snap1 = self.build_snapshot(backend)
        backend.executescript("CREATE TABLE t1 (id INTEGER PRIMARY KEY)")
        snap2 = self.build_snapshot(backend)
        from rhosocial.activerecord.backend.impl.sqlite.schema.differ import (
            SQLiteSchemaDiffer,
        )

        diff = SQLiteSchemaDiffer().compare(snap1, snap2)
        assert "t1" in diff.added_tables

    def test_removed_table_detected(self, backend):
        backend.executescript("CREATE TABLE t1 (id INTEGER PRIMARY KEY)")
        snap1 = self.build_snapshot(backend)
        backend.executescript("DROP TABLE t1")
        snap2 = self.build_snapshot(backend)
        from rhosocial.activerecord.backend.impl.sqlite.schema.differ import (
            SQLiteSchemaDiffer,
        )

        diff = SQLiteSchemaDiffer().compare(snap1, snap2)
        assert "t1" in diff.removed_tables

    def test_added_index_detected(self, backend):
        backend.executescript(
            "CREATE TABLE t1 (id INTEGER PRIMARY KEY, name TEXT)"
        )
        snap1 = self.build_snapshot(backend)
        backend.executescript("CREATE INDEX idx_name ON t1(name)")
        snap2 = self.build_snapshot(backend)
        from rhosocial.activerecord.backend.impl.sqlite.schema.differ import (
            SQLiteSchemaDiffer,
        )

        diff = SQLiteSchemaDiffer().compare(snap1, snap2)
        td = diff.table_diffs["t1"]
        assert len(td.added_indexes) == 1

    def test_removed_index_detected(self, backend):
        backend.executescript(
            "CREATE TABLE t1 (id INTEGER PRIMARY KEY, name TEXT)"
        )
        backend.executescript("CREATE INDEX idx_name ON t1(name)")
        snap1 = self.build_snapshot(backend)
        backend.executescript("DROP INDEX idx_name")
        snap2 = self.build_snapshot(backend)
        from rhosocial.activerecord.backend.impl.sqlite.schema.differ import (
            SQLiteSchemaDiffer,
        )

        diff = SQLiteSchemaDiffer().compare(snap1, snap2)
        td = diff.table_diffs["t1"]
        assert len(td.removed_indexes) == 1
