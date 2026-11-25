# tests/rhosocial/activerecord_test/feature/migration/test_schema_change_column_options.py
"""An option-only declaration change reaches the differ as a change."""

from typing import ClassVar, Optional

try:
    from typing import Annotated
except ImportError:  # Python 3.8
    from typing_extensions import Annotated

from rhosocial.activerecord.base import DDLAnnotationHandler, UseSqlType
from rhosocial.activerecord.backend.expression.types import VarCharType
from rhosocial.activerecord.backend.schema.differ import ColumnChangeKind
from rhosocial.activerecord.migration import diff_declarations
from rhosocial.activerecord.model import ActiveRecord
from support.column_options import (
    ColumnOptionAnnotation,
    ColumnOptionHandler,
    MarkerOption,
)

_HANDLERS = [DDLAnnotationHandler, ColumnOptionHandler]


def _model(name, option):
    """Build a model whose only varying fact is *option*."""

    class _Optioned(ActiveRecord):
        _feature_handlers: ClassVar[list] = _HANDLERS

        @classmethod
        def table_name(cls):
            return name

        id: Optional[int] = None
        label: Annotated[
            str,
            UseSqlType(VarCharType(length=50)),
            ColumnOptionAnnotation(option),
        ] = ""

    return _Optioned


_OLD = _model("optioned", MarkerOption("old"))
_NEW = _model("optioned", MarkerOption("new"))
_SAME = _model("optioned", MarkerOption("old"))


def test_a_new_option_instance_with_the_same_state_is_not_a_change():
    diff = diff_declarations(_OLD, _SAME)
    assert diff.table_diffs == {}


def test_an_option_value_change_is_a_modify_with_no_add_or_drop():
    diff = diff_declarations(_OLD, _NEW)
    table_diff = diff.table_diffs["optioned"]
    changes = table_diff.column_diffs

    assert [change.kind for change in changes] == [ColumnChangeKind.MODIFY]
    assert changes[0].column_name == "label"
    assert changes[0].old.column_options
    assert changes[0].new.column_options


def test_the_option_projection_names_the_class_and_its_state():
    diff = diff_declarations(_OLD, _NEW)
    change = diff.table_diffs["optioned"].column_diffs[0]

    old_signature = change.old.signature()
    new_signature = change.new.signature()
    assert old_signature != new_signature
    old_option = old_signature[-1][0]
    new_option = new_signature[-1][0]
    assert old_option[0] == "MarkerOption"
    assert new_option[0] == "MarkerOption"
    assert ("marker", "old") in old_option[1]
    assert ("marker", "new") in new_option[1]
