# tests/rhosocial/activerecord_test/feature/backend/core/test_alter_planner.py
"""The ALTER planner: declaration diff → ordered, executable statements.

Each change becomes its own AlterTableStatement (one expression = one SQL
statement). Changes the dialect cannot express are routed to a rebuild plan.
"""
from typing import Optional

try:
    from typing import Annotated
except ImportError:  # Python 3.8
    from typing_extensions import Annotated

from rhosocial.activerecord.backend.schema import AlterPlanner
from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
    AddColumnAction, DropColumnAction,
)
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


def test_add_and_drop_become_separate_statements():
    plan = AlterPlanner().plan(_Old, _New, DummyDialect())
    # gone dropped, added added — two independent statements, one action each
    assert len(plan.statements) == 2
    assert all(len(st.actions) == 1 for st in plan.statements)
    kinds = {type(st.actions[0]) for st in plan.statements}
    assert kinds == {AddColumnAction, DropColumnAction}


def test_plan_statements_are_individually_executable_sql():
    """Each statement renders one ALTER TABLE — no semicolon-joined strings."""
    plan = AlterPlanner().plan(_Old, _New, DummyDialect())
    for st in plan.statements:
        sql, _ = st.to_sql()
        assert sql.count("ALTER TABLE") == 1
        assert ";" not in sql


def test_identical_models_produce_empty_plan():
    plan = AlterPlanner().plan(_Old, _Old, DummyDialect())
    assert plan.is_empty


def test_no_hook_no_rebuild_for_plain_type_change():
    """A modify with no backend hook is reported as a rebuild, not bad SQL."""
    from rhosocial.activerecord.base import UseSqlType
    from rhosocial.activerecord.backend.expression.types import VarCharType

    class _Changed(ActiveRecord):
        @classmethod
        def table_name(cls):
            return "users"
        id: Optional[int] = None
        gone: Annotated[str, UseSqlType(VarCharType(length=64))] = ""

    plan = AlterPlanner().plan(_Old, _Changed, DummyDialect())
    # gone modified via no hook -> rebuild; no invalid statement emitted
    assert any(r.table_name == "users" for r in plan.rebuilds)
    assert all(len(st.actions) == 1 for st in plan.statements)
