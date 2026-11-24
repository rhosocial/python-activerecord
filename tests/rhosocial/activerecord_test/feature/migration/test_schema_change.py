# tests/rhosocial/activerecord_test/feature/migration/test_schema_change.py
"""ActiveRecord-layer schema change: model diff → core ALTER expressions.

Layering (layer-separation.md A1/A2): this lives in A, reads model declarations,
emits backend expression instances through the contract. Backend never sees AR.
Mechanism (suggestion.md §3.4): single-action changes emit expressions directly;
multi-step changes are named suggestion points, not hard-coded strategies.
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
    added: str = ""


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
    assert added.new.python_type is str


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
