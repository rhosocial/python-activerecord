# tests/rhosocial/activerecord_test/feature/backend/core/test_schema_diff_vocabulary.py
"""The diff vocabulary a migration planner consumes.

The original SchemaDiff expressed only add/remove/modify by name. A planner
also needs change *kinds* (rename vs drop+add), reorder intent, table options
and a rebuild flag. These tests pin that the enriched data model carries them,
without changing the existing is_added/is_removed/is_modified semantics.
"""
from rhosocial.activerecord.backend.introspection.types import (
    IntrospectionColumnInfo,
    IntrospectionTableInfo,
)
from rhosocial.activerecord.backend.schema import SchemaDiffer
from rhosocial.activerecord.backend.schema.differ import (
    ColumnChangeKind,
    ColumnDiff,
    TableDiff,
)


def _col(name, ordinal=1):
    return IntrospectionColumnInfo(
        name=name, table_name="t", data_type="INTEGER", ordinal_position=ordinal
    )


def test_column_diff_kind_defaults_preserve_legacy_semantics():
    """Old construction (no kind) still works and reports modify."""
    cd = ColumnDiff("c", _col("c"), _col("c"))
    assert cd.kind is ColumnChangeKind.MODIFY
    assert cd.is_modified
    assert not cd.is_renamed


def test_column_diff_rename_carries_old_and_new_name():
    cd = ColumnDiff(
        "old_name", _col("old_name"), _col("new_name"),
        kind=ColumnChangeKind.RENAME, new_name="new_name",
    )
    assert cd.is_renamed
    assert cd.column_name == "old_name"
    assert cd.new_name == "new_name"


def test_diff_reports_add_drop_modify_kinds():
    differ = SchemaDiffer()
    old = IntrospectionTableInfo(
        name="t", columns=[_col("keep"), _col("gone", 2)], comment="old"
    )
    new = IntrospectionTableInfo(
        name="t", columns=[_col("keep"), _col("added", 2)], comment="new"
    )
    td = differ._diff_table("t", old, new)
    kinds = {cd.column_name: cd.kind for cd in td.column_diffs}
    assert kinds["gone"] is ColumnChangeKind.DROP
    assert kinds["added"] is ColumnChangeKind.ADD
    # keep has identical type/nullable/default so no modify diff
    assert "keep" not in kinds
    assert td.comment_changed is True


def test_diff_reports_reordered_columns():
    differ = SchemaDiffer()
    old = IntrospectionTableInfo(
        name="t", columns=[_col("a", 1), _col("b", 2)]
    )
    new = IntrospectionTableInfo(
        name="t", columns=[_col("b", 1), _col("a", 2)]
    )
    td = differ._diff_table("t", old, new)
    assert set(td.reordered_columns) == {"a", "b"}
    assert td.has_changes


def test_table_diff_additive_fields_default_empty():
    """A plain TableDiff stays valid and unchanged in has_changes."""
    td = TableDiff("t", None, None)
    assert td.reordered_columns == []
    assert td.comment_changed is False
    assert td.requires_rebuild is False
    assert td.rebuild_reason is None
    assert td.has_changes  # is_added


def test_column_equivalence_detects_comment_and_generated_changes():
    """Comment / charset / identity are compared, not silently ignored."""
    differ = SchemaDiffer()
    base = _col("c")
    base.comment = "old"
    base.collation = "BINARY"

    by_comment = _col("c")
    by_comment.comment = "new"
    by_comment.collation = "BINARY"
    assert not differ._columns_equivalent(base, by_comment)

    by_collation = _col("c")
    by_collation.comment = "old"
    by_collation.collation = "NOCASE"
    assert not differ._columns_equivalent(base, by_collation)

    by_generated = _col("c")
    by_generated.comment = "old"
    by_generated.collation = "BINARY"
    by_generated.is_generated = True
    assert not differ._columns_equivalent(base, by_generated)

    # Equal on all compared fields -> equivalent
    same = _col("c")
    same.comment = "old"
    same.collation = "BINARY"
    assert differ._columns_equivalent(base, same)


def test_string_fields_compared_only_when_both_present():
    """A backend that cannot read a field must not create a spurious diff."""
    differ = SchemaDiffer()
    a = _col("c")
    b = _col("c")
    b.comment = None  # both effectively unread
    a.comment = None
    assert differ._columns_equivalent(a, b)
    # one side has a value, other is None -> not a false positive
    b.comment = "x"
    assert differ._columns_equivalent(a, b)  # old unread, so no spurious diff
