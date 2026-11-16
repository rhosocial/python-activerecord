# tests/rhosocial/activerecord_test/feature/basic/ddl/test_ddl_suggested_storage_types.py
"""The suggested storage-type layer: table, lookup, and derived identity.

Three things are under contract here:

* the two tables (suggested + backend's own) answer every framework-modelled
  24 keys, with instances that are renderable and **copies**;
* a field that declares no SQL type takes the suggestion, and one that
  declares its own type keeps it;
* a single-column integer primary key the model says the database generates
  is declared as an identity, because the write path already asks the caller
  for nothing there.
"""
try:  # Python 3.8 has no typing.Annotated
    from typing import Annotated, Optional
except ImportError:  # pragma: no cover - only on 3.8
    from typing import Optional

    from typing_extensions import Annotated

import pytest

from rhosocial.activerecord.backend.dialect.mixins import StorageTypeMixin
from rhosocial.activerecord.backend.dialect.protocols import StorageTypeSupport
from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.base.derivation import build_create_table_statement
from rhosocial.activerecord.backend.expression.types import (
    BooleanType,
    IntegerType,
    TextType,
    VarCharType,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.base.framework_types import FRAMEWORK_PYTHON_TYPES
from rhosocial.activerecord.field import CompositePKMixin
from rhosocial.activerecord.model import ActiveRecord


def _create(model, dialect=None):
    dialect = dialect or SQLiteDialect()
    return build_create_table_statement(model, dialect).to_sql()[0]


class BareRow(ActiveRecord):
    """Nothing but Python types: the model a suggestion has to carry."""

    @classmethod
    def table_name(cls):
        return "bare_rows"

    id: Optional[int] = None
    name: str
    note: Optional[str] = None
    flag: bool = True


class DeclaredRow(ActiveRecord):
    """The same columns, each with the suggestion spelled out."""

    @classmethod
    def table_name(cls):
        return "declared_rows"

    id: Annotated[Optional[int], UseSqlType(IntegerType())] = None
    name: Annotated[str, UseSqlType(TextType())]
    note: Annotated[Optional[str], UseSqlType(TextType())] = None
    flag: Annotated[bool, UseSqlType(BooleanType())]


class Uninferable(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "uninferable"

    id: Optional[int] = None
    payload: object


class AppKey(ActiveRecord):
    """The application writes its own key, so no identity is implied."""

    @classmethod
    def table_name(cls):
        return "app_key"

    @classmethod
    def pk_auto_generated(cls):
        return False

    id: Optional[int] = None
    name: str


class CompositeKey(CompositePKMixin, ActiveRecord):
    @classmethod
    def table_name(cls):
        return "composite_key"

    @classmethod
    def primary_key(cls):
        return ("id", "bucket")

    id: int = 0
    bucket: int = 0
    name: str


class NonIntegerKey(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "non_integer_key"

    id: Optional[str] = None
    name: str


# ---------------------------------------------------------------------------
# 1. The two tables
# ---------------------------------------------------------------------------


def test_the_mixin_withholds_the_suggested_table():
    class Bare(StorageTypeMixin):
        pass

    with pytest.raises(NotImplementedError, match="suggested storage-type"):
        Bare().suggested_storage_types()
    assert Bare().suggested_extra_storage_types() == {}


def test_the_protocol_is_structural():
    dialect = SQLiteDialect()
    assert isinstance(dialect, StorageTypeSupport)
    assert callable(dialect.suggested_storage_types)
    assert callable(dialect.suggested_extra_storage_types)


@pytest.mark.parametrize("dialect_factory", [SQLiteDialect, DummyDialect])
def test_every_framework_type_is_answered(dialect_factory):
    dialect = dialect_factory()
    table = dialect.suggested_storage_types()
    missing = [entry for entry in FRAMEWORK_PYTHON_TYPES if entry not in table]
    assert missing == []


@pytest.mark.parametrize("dialect_factory", [SQLiteDialect, DummyDialect])
def test_every_answer_is_renderable_or_a_stated_none(dialect_factory):
    dialect = dialect_factory()
    for suggestion in dialect.suggested_storage_types().values():
        if suggestion is None:
            continue
        # Renderable: the suggestion is a declaration the dialect can spell.
        dialect.format_data_type(suggestion)


@pytest.mark.parametrize("dialect_factory", [SQLiteDialect, DummyDialect])
def test_the_tables_hand_out_copies(dialect_factory):
    dialect = dialect_factory()
    first = dialect.suggested_storage_types()
    second = dialect.suggested_storage_types()

    assert first is not second
    for entry in FRAMEWORK_PYTHON_TYPES:
        if first[entry] is None:
            assert second[entry] is None
            continue
        assert first[entry] is not second[entry]


def test_binding_a_returned_instance_does_not_leak_into_the_table():
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

    dialect = SQLiteDialect()
    suggested = dialect.suggested_storage_types()[str]
    suggested.dialect = dialect

    fresh = SQLiteDialect().suggested_storage_types()[str]
    with pytest.raises(ValueError, match="has no dialect bound"):
        _ = fresh.dialect
    assert fresh == suggested


def test_the_extra_table_is_disjoint_from_the_suggested_one():
    dialect = SQLiteDialect()
    assert dialect.suggested_extra_storage_types() == {}
    assert set(dialect.suggested_storage_types()).isdisjoint(
        dialect.suggested_extra_storage_types()
    )


# ---------------------------------------------------------------------------
# 2. The suggestion is what a bare field gets
# ---------------------------------------------------------------------------


def test_a_bare_field_takes_the_suggestion():
    sql = _create(BareRow)

    assert '"id" INTEGER PRIMARY KEY AUTOINCREMENT' in sql
    assert '"name" TEXT NOT NULL' in sql
    assert '"note" TEXT' in sql
    assert '"flag" NUMERIC NOT NULL' in sql


def test_a_bare_model_and_its_spelled_out_twin_derive_the_same_columns():
    bare = _create(BareRow).replace("bare_rows", "rows")
    declared = _create(DeclaredRow).replace("declared_rows", "rows")

    assert bare == declared


def test_a_declared_type_beats_the_suggestion():
    class Declared(ActiveRecord):
        @classmethod
        def table_name(cls):
            return "declared"

        id: Optional[int] = None
        name: Annotated[str, UseSqlType(VarCharType(length=32))]

    sql = _create(Declared)

    assert '"name" TEXT NOT NULL' in sql  # SQLite stores VarChar as TEXT
    assert isinstance(Declared.column_data_type("name").data_type, VarCharType)


def test_a_type_the_dialect_does_not_suggest_is_an_error_naming_the_column():
    with pytest.raises(ValueError) as caught:
        _create(Uninferable)

    message = str(caught.value)
    assert "uninferable.payload" in message
    assert "declares no SQL type" in message
    assert "object" in message
    assert "UseSqlType" in message


# ---------------------------------------------------------------------------
# 3. Identity is derived where the write path promises it
# ---------------------------------------------------------------------------


def test_a_single_integer_primary_key_gets_an_identity():
    """``required_pk_fields()`` asks the caller for nothing, so the DDL says so."""
    assert BareRow.required_pk_fields() == ()
    assert "INTEGER PRIMARY KEY AUTOINCREMENT" in _create(BareRow)


def test_an_application_written_key_gets_no_identity():
    assert AppKey.pk_auto_generated() is False
    assert "AUTOINCREMENT" not in _create(AppKey)


def test_a_composite_key_gets_no_identity():
    assert "AUTOINCREMENT" not in _create(CompositeKey)


def test_a_non_integer_key_gets_no_identity():
    assert "AUTOINCREMENT" not in _create(NonIntegerKey)
