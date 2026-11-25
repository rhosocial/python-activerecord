# tests/rhosocial/activerecord_test/feature/migration/test_schema_change.py
"""ActiveRecord-layer schema change: model diff → core ALTER expressions.

Layering (layer-separation.md A1/A2): this lives in A, reads model declarations,
emits backend expression instances through the contract. Backend never sees AR.
Mechanism (suggestion.md §3.4): single-action changes emit expressions directly;
multi-step changes are frozen suggestion-point objects, not hard-coded strategies.
A conservatively recognised rename (one removal + one addition, equivalent except
the name) is also a single action; ambiguous cases stay drop+add.
"""
from typing import Optional

try:
    from typing import Annotated
except ImportError:  # Python 3.8
    from typing_extensions import Annotated

from rhosocial.activerecord.migration import diff_declarations, plan_changes
from rhosocial.activerecord.migration.schema_change import FieldChange
from rhosocial.activerecord.backend.schema.differ import ColumnChangeKind
from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.backend.expression.types import VarCharType
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.model import ActiveRecord


class _Old(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "users"

    id: Optional[int] = None
    gone: str = ""


class _New(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "users"

    id: Optional[int] = None
    # A different declared type keeps this a genuine drop+add rather than a
    # rename candidate (the two sides are not equivalent except for the name).
    added: int = 0


class _RenameOld(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "users"

    id: Optional[int] = None
    legacy_label: str = ""


class _RenameNew(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "users"

    id: Optional[int] = None
    current_label: str = ""


class _AmbiguousOld(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "users"

    id: Optional[int] = None
    alpha: str = ""
    beta: str = ""


class _AmbiguousNew(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "users"

    id: Optional[int] = None
    gamma: str = ""
    delta: str = ""


class _TypeChangedOld(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "users"

    id: Optional[int] = None
    old_field: str = ""


class _TypeChangedNew(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "users"

    id: Optional[int] = None
    new_field: int = 0


def test_diff_is_field_by_field_table_by_table():
    d = diff_declarations(_Old, _New)
    td = d.table_diffs["users"]
    adds = [cd for cd in td.column_diffs if cd.kind is ColumnChangeKind.ADD]
    drops = [cd for cd in td.column_diffs if cd.kind is ColumnChangeKind.DROP]
    assert [cd.column_name for cd in adds] == ["added"]
    assert [cd.column_name for cd in drops] == ["gone"]


def test_diff_payload_carries_declaration_facts():
    d = diff_declarations(_Old, _New)
    td = d.table_diffs["users"]
    added = next(cd for cd in td.column_diffs if cd.kind is ColumnChangeKind.ADD)
    assert isinstance(added.new, FieldChange)
    assert added.new.name == "added"
    assert added.new.python_type is int


def test_identical_declarations_produce_no_diff():
    assert diff_declarations(_Old, _Old).is_empty


def test_plan_emits_one_expression_per_single_action_change():
    plan = plan_changes(_Old, _New, DummyDialect())
    assert len(plan.statements) == 2
    assert all(len(st.actions) == 1 for st in plan.statements)


def test_plan_statements_are_individually_executable_sql():
    plan = plan_changes(_Old, _New, DummyDialect())
    for st in plan.statements:
        sql, _ = st.to_sql()
        assert sql.count("ALTER TABLE") == 1
        assert ";" not in sql


def test_no_probe_check_in_a_side_planning():
    """A side emits the neutral core expression; capability is B's formatter.

    A dialect whose formatter refuses the action fails fast at to_sql(), not via
    an A-side supports_* check. We assert the plan holds a core AlterColumnAction
    for a type change regardless of probe values.
    """
    class _Changed(ActiveRecord):
        @classmethod
        def table_name(cls):
            return "users"
        id: Optional[int] = None
        gone: Annotated[str, UseSqlType(VarCharType(length=64))] = ""

    plan = plan_changes(_Old, _Changed, DummyDialect())
    # One MODIFY statement emitted; no A-side capability gating happened.
    assert len(plan.statements) == 1
    from rhosocial.activerecord.backend.expression.statements.ddl_alter import AlterColumnAction
    assert isinstance(plan.statements[0].actions[0], AlterColumnAction)


def test_multi_step_changes_become_suggestion_points():
    """Reorder / partition changes are named δ, not hard-coded strategies."""
    class _Reordered(ActiveRecord):
        @classmethod
        def table_name(cls):
            return "users"
        # swap the order of the two common columns
        gone: str = ""
        id: Optional[int] = None

    plan = plan_changes(_Old, _Reordered, DummyDialect())
    assert "column_reorder" in plan.suggestion_points


def _kinds(td):
    return [(cd.kind, cd.column_name, cd.new_name) for cd in td.column_diffs]


def test_rename_detected_when_one_removal_and_one_addition_match():
    """A lone drop+add with equivalent declarations is a rename, not data loss."""
    td = diff_declarations(_RenameOld, _RenameNew).table_diffs["users"]
    renames = [cd for cd in td.column_diffs if cd.kind is ColumnChangeKind.RENAME]
    assert len(renames) == 1
    assert renames[0].column_name == "legacy_label"
    assert renames[0].new_name == "current_label"
    assert renames[0].is_renamed
    assert not [cd for cd in td.column_diffs if cd.kind in (ColumnChangeKind.DROP, ColumnChangeKind.ADD)]


def test_rename_becomes_a_single_rename_column_action():
    plan = plan_changes(_RenameOld, _RenameNew, DummyDialect())
    assert len(plan.statements) == 1
    from rhosocial.activerecord.backend.expression.statements.ddl_alter import RenameColumnAction
    action = plan.statements[0].actions[0]
    assert isinstance(action, RenameColumnAction)
    assert (action.old_name, action.new_name) == ("legacy_label", "current_label")
    sql, _ = plan.statements[0].to_sql()
    assert "RENAME COLUMN" in sql


def test_ambiguous_rename_is_not_paired():
    """More than one candidate on a side stays drop+add: no guessing."""
    td = diff_declarations(_AmbiguousOld, _AmbiguousNew).table_diffs["users"]
    kinds = _kinds(td)
    assert not any(kind is ColumnChangeKind.RENAME for kind, _, _ in kinds)
    assert sorted(name for kind, name, _ in kinds if kind is ColumnChangeKind.DROP) == ["alpha", "beta"]
    assert sorted(name for kind, name, _ in kinds if kind is ColumnChangeKind.ADD) == ["delta", "gamma"]


def test_type_changed_candidate_is_not_paired():
    """A data-affecting change on either side forbids the rename shortcut."""
    td = diff_declarations(_TypeChangedOld, _TypeChangedNew).table_diffs["users"]
    kinds = _kinds(td)
    assert [(kind, name) for kind, name, _ in kinds] == [
        (ColumnChangeKind.DROP, "old_field"),
        (ColumnChangeKind.ADD, "new_field"),
    ]


def test_plain_add_and_drop_stay_unpaired():
    """Distinct declarations on the two sides keep the original vocabulary."""
    td = diff_declarations(_Old, _New).table_diffs["users"]
    assert [(cd.kind, cd.column_name) for cd in td.column_diffs] == [
        (ColumnChangeKind.DROP, "gone"),
        (ColumnChangeKind.ADD, "added"),
    ]
