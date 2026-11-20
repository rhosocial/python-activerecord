# tests/rhosocial/activerecord_test/feature/backend/sqlite/native/test_native_virtual_tables.py
"""Virtual tables must not become reachable through ordinary field mapping.

SQLite's FTS5 and R*Tree are *virtual* tables: the module materialises shadow
tables next to the declared one, and both the virtual table and its shadows
live in ``sqlite_master`` like ordinary tables.  An ORM that resolved a field
by "some table with that column" instead of by the model's own table would
start reading (or writing) full-text or spatial index storage.

The check is deliberately indirect: a normal model row and a virtual-table row
hold *different* text under the same column name, so any cross-use shows up as
the wrong value rather than as a subtle count difference.
"""

import pytest

from rhosocial.activerecord.backend.adapters.geometry import Point

FTS_TABLE = "vt_native_fts"
RTREE_TABLE = "vt_native_rtree"

MODEL_SHAPE = Point(1.5, 2.5)
FTS_CONTENT = "POINT (9.0 9.0)"


def _master_row(model, name: str):
    return model.backend().fetch_one("SELECT type, sql FROM sqlite_master WHERE name = ?", (name,))


def _create_fts(model) -> None:
    model.backend().execute(f"CREATE VIRTUAL TABLE {FTS_TABLE} USING fts5(content)")
    model.backend().execute(f"INSERT INTO {FTS_TABLE} (content) VALUES (?)", (FTS_CONTENT,))


def _create_rtree(model) -> None:
    model.backend().execute(
        f"CREATE VIRTUAL TABLE {RTREE_TABLE} " "USING rtree(id, minx, maxx, miny, maxy)"
    )
    model.backend().execute(
        f"INSERT INTO {RTREE_TABLE} (id, minx, maxx, miny, maxy) VALUES (1, ?, ?, ?, ?)",
        (100.0, 200.0, 100.0, 200.0),
    )


def test_fts5_virtual_table_is_not_used_by_a_normal_model(affinity_models, database):
    """A full-text index next to the model's table stays invisible to the model."""
    if not database.dialect.supports_fts5():
        pytest.skip("environment: this SQLite build has no FTS5 module")

    model = affinity_models["text"]
    _create_fts(model)
    try:
        instance = model(shape=MODEL_SHAPE)
        instance.save()

        found = model.find_one(instance.id)
        assert (
            found.shape == MODEL_SHAPE
        ), "the model must read its own row, not the full-text index"

        # The index still holds its own, different, text.
        fts_row = model.backend().fetch_one(f"SELECT content FROM {FTS_TABLE}")
        assert fts_row["content"] == FTS_CONTENT

        # And it is a virtual table, while the model's table is not.
        assert _master_row(model, FTS_TABLE)["sql"].upper().startswith("CREATE VIRTUAL TABLE")
        assert _master_row(model, model.table_name())["sql"].upper().startswith("CREATE TABLE")

        # FTS5 materialises shadow tables; none of them is a model column.
        shadow_tables = {"f_config", "f_content", "f_data", "f_docsize", "f_idx"}
        columns = set(model.get_column_to_field_map())
        assert "content" not in columns
        assert columns.isdisjoint(shadow_tables)
    finally:
        model.backend().execute(f"DROP TABLE IF EXISTS {FTS_TABLE}")


def test_rtree_virtual_table_is_not_used_by_a_normal_model(affinity_models, database):
    """A spatial index next to the model's table stays invisible to the model."""
    if not database.dialect.supports_rtree():
        pytest.skip("environment: this SQLite build has no R*Tree module")

    model = affinity_models["text"]
    _create_rtree(model)
    try:
        instance = model(counter=42, ratio=2.5)
        instance.save()

        found = model.find_one(instance.id)
        assert found.counter == 42
        assert found.ratio == 2.5

        rtree_row = model.backend().fetch_one(
            f"SELECT id, minx, maxx, miny, maxy FROM {RTREE_TABLE}"
        )
        assert (rtree_row["minx"], rtree_row["maxx"]) == (100.0, 200.0)

        assert _master_row(model, RTREE_TABLE)["sql"].upper().startswith("CREATE VIRTUAL TABLE")

        # R*Tree's shadow tables and coordinate columns are not model columns.
        columns = set(model.get_column_to_field_map())
        assert {"minx", "maxx", "miny", "maxy"}.isdisjoint(columns)
        assert {"r_node", "r_parent", "r_rowid"}.isdisjoint(columns)
    finally:
        model.backend().execute(f"DROP TABLE IF EXISTS {RTREE_TABLE}")


def test_shadow_tables_do_not_share_the_model_name(affinity_models, database):
    """The model's table name is its own; shadow tables are named after the index."""
    if not database.dialect.supports_fts5():
        pytest.skip("environment: this SQLite build has no FTS5 module")

    model = affinity_models["text"]
    _create_fts(model)
    try:
        names = {
            row["name"]
            for row in model.backend().fetch_all(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert model.table_name() in names
        assert f"{FTS_TABLE}_data" in names
        assert model.table_name() not in {
            f"{FTS_TABLE}_config",
            f"{FTS_TABLE}_content",
            f"{FTS_TABLE}_data",
            f"{FTS_TABLE}_docsize",
            f"{FTS_TABLE}_idx",
        }
    finally:
        model.backend().execute(f"DROP TABLE IF EXISTS {FTS_TABLE}")
