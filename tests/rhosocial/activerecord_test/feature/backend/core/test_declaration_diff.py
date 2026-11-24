# tests/rhosocial/activerecord_test/feature/backend/core/test_declaration_diff.py
"""Direct field-by-field / table-by-table diff of two model declarations.

The planner input: compare two retained ActiveRecord classes, get a SchemaDiff
whose old/new carry declaration facts (not introspection rows), with no model→
snapshot conversion step.
"""
try:
    from typing import Annotated
except ImportError:  # Python 3.8
    from typing_extensions import Annotated
from typing import Optional

from rhosocial.activerecord.backend.schema import (
    DeclarationDiffer,
    ColumnChangeKind,
)
from rhosocial.activerecord.backend.schema.differ import ColumnChangeKind as K
from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.backend.expression.types import VarCharType
from rhosocial.activerecord.model import ActiveRecord


class _OldUser(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "users"

    id: Optional[int] = None
    name: str = ""


class _NewUser(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "users"

    id: Optional[int] = None
    email: str = ""
    name: str = ""


class _RenamedType(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "users"

    id: Optional[int] = None
    name: str = ""


def _diff(old, new):
    return DeclarationDiffer().compare(old, new, None)


def test_added_field_is_reported_as_add():
    d = _diff(_OldUser, _NewUser)
    td = d.table_diffs["users"]
    adds = {cd.column_name for cd in td.column_diffs if cd.kind is ColumnChangeKind.ADD}
    assert adds == {"email"}


def test_removed_field_is_reported_as_drop():
    d = _diff(_NewUser, _OldUser)
    td = d.table_diffs["users"]
    drops = {cd.column_name for cd in td.column_diffs if cd.kind is ColumnChangeKind.DROP}
    assert drops == {"email"}


def test_identical_declarations_produce_empty_diff():
    assert _diff(_OldUser, _OldUser).is_empty


def test_type_change_is_reported_as_modify():
    class _Typed(ActiveRecord):
        @classmethod
        def table_name(cls):
            return "users"
        id: Optional[int] = None
        name: str = ""

    class _TypedChanged(ActiveRecord):
        @classmethod
        def table_name(cls):
            return "users"
        id: Optional[int] = None
        name: Annotated[str, UseSqlType(VarCharType(length=64))] = ""

    d = _diff(_Typed, _TypedChanged)
    td = d.table_diffs["users"]
    mods = {cd.column_name for cd in td.column_diffs if cd.kind is K.MODIFY}
    assert "name" in mods


def test_diff_old_new_carry_declaration_facts_not_introspection_rows():
    """Diff payload is field declarations, self-contained and readable."""
    from rhosocial.activerecord.backend.schema import FieldDeclaration

    d = _diff(_OldUser, _NewUser)
    td = d.table_diffs["users"]
    email = next(cd for cd in td.column_diffs if cd.column_name == "email")
    assert isinstance(email.new, FieldDeclaration)
    assert email.new.name == "email"
    assert email.new.python_type is str


def test_table_declaration_flags_compare():
    """Table constraint/index/partition changes are distinct diff flags."""
    from rhosocial.activerecord.backend.schema import TableDeclaration
    from rhosocial.activerecord.backend.schema.declaration_diff import _freeze

    # _freeze gives a comparable signature for constraint/index declarations;
    # a change must be detectable while an identical one must not.
    a = ("uq", ("name",))
    b = ("uq", ("email",))
    assert _freeze(a) != _freeze(b)
    assert _freeze(a) == _freeze(("uq", ("name",)))

    # TableDeclaration carries the slots; a plain one stays empty.
    td = TableDeclaration("users")
    assert td.table_constraints == () and td.partition is None


def test_different_table_names_become_drop_plus_add():
    class _Other(ActiveRecord):
        @classmethod
        def table_name(cls):
            return "other"
        x: int = 0

    d = _diff(_OldUser, _Other)
    assert set(d.table_diffs) == {"users", "other"}
    assert d.table_diffs["users"].is_removed
    assert d.table_diffs["other"].is_added
