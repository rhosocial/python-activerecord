# tests/rhosocial/activerecord_test/feature/ddl/core/test_column_options_application.py
"""Declared column options choose the column class and are actually applied."""

from typing import ClassVar, Optional

try:
    from typing import Annotated
except ImportError:  # Python 3.8
    from typing_extensions import Annotated

import pytest

from rhosocial.activerecord.base import DDLAnnotationHandler, UseSqlType
from rhosocial.activerecord.base.derivation import (
    build_column_definitions,
    build_create_table_statement,
)
from rhosocial.activerecord.backend.expression.statements import ColumnDefinition
from rhosocial.activerecord.backend.expression.types import VarCharType
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.model import ActiveRecord
from support.column_options import (
    BrokenOption,
    ColumnOptionAnnotation,
    ColumnOptionHandler,
    CollationOption,
    FakeColumnDefinition,
    MarkerOption,
    OtherOption,
    SilentOption,
)

_HANDLERS = [DDLAnnotationHandler, ColumnOptionHandler]


class _Plain(ActiveRecord):
    _feature_handlers: ClassVar[list] = _HANDLERS

    @classmethod
    def table_name(cls):
        return "plain_options"

    id: Optional[int] = None
    label: Annotated[str, UseSqlType(VarCharType(length=50))] = ""


class _Optioned(ActiveRecord):
    _feature_handlers: ClassVar[list] = _HANDLERS

    @classmethod
    def table_name(cls):
        return "optioned"

    id: Optional[int] = None
    label: Annotated[
        str,
        UseSqlType(VarCharType(length=50)),
        ColumnOptionAnnotation(
            CollationOption("und:ci"),
            MarkerOption("marker"),
        ),
    ] = ""


class _Conflicting(ActiveRecord):
    _feature_handlers: ClassVar[list] = _HANDLERS

    @classmethod
    def table_name(cls):
        return "conflicting"

    id: Optional[int] = None
    label: Annotated[
        str,
        UseSqlType(VarCharType(length=50)),
        ColumnOptionAnnotation(CollationOption("und:ci"), OtherOption()),
    ] = ""


class _Broken(ActiveRecord):
    _feature_handlers: ClassVar[list] = _HANDLERS

    @classmethod
    def table_name(cls):
        return "broken"

    id: Optional[int] = None
    label: Annotated[
        str,
        UseSqlType(VarCharType(length=50)),
        ColumnOptionAnnotation(BrokenOption()),
    ] = ""


class _Silent(ActiveRecord):
    _feature_handlers: ClassVar[list] = _HANDLERS

    @classmethod
    def table_name(cls):
        return "silent"

    id: Optional[int] = None
    label: Annotated[
        str,
        UseSqlType(VarCharType(length=50)),
        ColumnOptionAnnotation(SilentOption("value")),
    ] = ""


def _column_named(columns, name):
    return next(column for column in columns if column.name == name)


def test_options_select_the_column_class_and_transfer_state():
    dialect = DummyDialect()
    columns = build_column_definitions(_Optioned, dialect)

    label = _column_named(columns, "label")
    assert type(label) is FakeColumnDefinition
    assert label.applied_collations == ["und:ci"]
    assert label.marker == "marker"

    sql, params = build_create_table_statement(_Optioned, dialect).to_sql()
    assert "COLLATE und:ci" in sql
    assert params == ()


def test_multiple_options_are_applied_in_declaration_order():
    dialect = DummyDialect()
    columns = build_column_definitions(_Optioned, dialect)

    label = _column_named(columns, "label")
    # The two options ran in the order the annotation listed them.
    assert label.applied_collations == ["und:ci"]
    assert label.marker == "marker"
    clauses = [type(clause).__name__ for clause in label.attributes]
    assert "CollationClause" in clauses


def test_conflicting_column_classes_are_refused_by_name():
    with pytest.raises(ValueError) as caught:
        build_column_definitions(_Conflicting, DummyDialect())

    message = str(caught.value)
    assert "label" in message
    assert "FakeColumnDefinition" in message
    assert "OtherColumnDefinition" in message


def test_no_options_keeps_the_core_column_definition():
    dialect = DummyDialect()
    columns = build_column_definitions(_Plain, dialect)
    label = _column_named(columns, "label")

    assert type(label) is ColumnDefinition
    assert list(label.attributes) == []
    assert label.constraints
    reference = ColumnDefinition(
        dialect,
        label.name,
        label.data_type,
        constraints=label.constraints,
        comment=label.comment,
        generated_expression=label.generated_expression,
        attributes=label.attributes,
    )
    assert label.to_sql() == reference.to_sql()


def test_an_apply_to_failure_names_the_field_and_the_classes():
    with pytest.raises(TypeError) as caught:
        build_column_definitions(_Broken, DummyDialect())

    message = str(caught.value)
    assert "broken.label" in message
    assert "BrokenOption.apply_to" in message
    assert "FakeColumnDefinition" in message


def test_a_silent_apply_to_no_op_is_refused():
    with pytest.raises(TypeError) as caught:
        build_column_definitions(_Silent, DummyDialect())

    message = str(caught.value)
    assert "silent.label" in message
    assert "SilentOption" in message
    assert "dropped silently" in message
