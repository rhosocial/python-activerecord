# tests/rhosocial/activerecord_test/feature/basic/ddl/test_ddl_suggested_data_types.py
"""The suggested data-type layer: the table, the lookup, and derived identity.

Three things are under contract here:

* the table answers every framework-modelled type with a **renderable**
   ``DataType`` -- there is no ``None`` answer, because a bare field always
   has a declaration -- and the backend's own table is separate and disjoint;
* a field that declares no SQL type takes the suggestion, and one that declares
   its own type keeps it;
* a single-column integer primary key the model says the database generates
   is declared as an identity, because the write path already asks the caller
   for nothing there.

The table hands out a fresh **dict** whose values are the module's read-only
templates; the derivation copies the one entry it binds. That is the cheap
and safe shape measured for this layer: copying the whole table per call cost
about 100 us, more than constructing fresh instances, and nothing needs more
than one entry.
"""
try:  # Python 3.8 has no typing.Annotated
    from typing import Annotated, Optional
except ImportError:  # pragma: no cover - only on 3.8
    from typing import Optional

    from typing_extensions import Annotated

import pytest

from rhosocial.activerecord.backend.dialect.mixins import DataTypeMixin
from rhosocial.activerecord.backend.dialect.protocols import DataTypeSupport
from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.base.derivation import (
    _INTEGER_CONCEPTS,
    build_create_table_statement,
)
from rhosocial.activerecord.backend.expression.types import (
    BooleanType,
    IntegerType,
    TextType,
    VarCharType,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.dummy.data_type_suggestions import (
    DUMMY_DATA_TYPE_SUGGESTIONS,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.mixins.data_type_suggestions import (
    SQLITE_DATA_TYPE_SUGGESTIONS,
)
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
    class Bare(DataTypeMixin):
        pass

    with pytest.raises(NotImplementedError, match="suggested data-type"):
        Bare().suggested_data_types()
    assert Bare().suggested_extra_data_types() == {}


def test_the_protocol_is_structural():
    dialect = SQLiteDialect()
    assert isinstance(dialect, DataTypeSupport)
    assert callable(dialect.suggested_data_types)
    assert callable(dialect.suggested_extra_data_types)


@pytest.mark.parametrize("dialect_factory", [SQLiteDialect, DummyDialect])
def test_every_framework_type_is_answered(dialect_factory):
    dialect = dialect_factory()
    table = dialect.suggested_data_types()
    missing = [entry for entry in FRAMEWORK_PYTHON_TYPES if entry not in table]
    assert missing == []


@pytest.mark.parametrize("dialect_factory", [SQLiteDialect, DummyDialect])
def test_nothing_is_left_unanswered(dialect_factory):
    """A suggestion is what a bare field gets, so ``None`` would take the table
    away from the caller. The commitment is that every framework-modelled type
    has a declaration; a precise spelling is the field's business."""
    dialect = dialect_factory()
    unanswered = [entry.__name__ for entry, value in dialect.suggested_data_types().items() if value is None]
    assert unanswered == []


@pytest.mark.parametrize("dialect_factory", [SQLiteDialect, DummyDialect])
def test_every_answer_is_renderable(dialect_factory):
    dialect = dialect_factory()
    for suggestion in dialect.suggested_data_types().values():
        # Renderable: the suggestion is a declaration the dialect can spell.
        dialect.format_data_type(suggestion)


@pytest.mark.parametrize("dialect_factory", [SQLiteDialect, DummyDialect])
def test_each_call_returns_a_fresh_dict(dialect_factory):
    dialect = dialect_factory()
    first = dialect.suggested_data_types()
    second = dialect.suggested_data_types()

    assert first is not second
    assert first == second


def test_the_tables_agree_with_the_module_level_constants():
    """One table, one source: each dialect answers the documented constant, so a
    future edit that makes one of them compute something else fails here,
    naming the drift."""
    assert SQLiteDialect().suggested_data_types() == SQLITE_DATA_TYPE_SUGGESTIONS
    assert SQLiteDialect().suggested_data_types() is not SQLITE_DATA_TYPE_SUGGESTIONS
    assert DummyDialect().suggested_data_types() == DUMMY_DATA_TYPE_SUGGESTIONS
    assert DummyDialect().suggested_data_types() is not DUMMY_DATA_TYPE_SUGGESTIONS


def test_the_values_are_the_read_only_templates():
    """The table is not rebuilt per call: its values are the module's templates.
    A caller binds a rendering on a **copy**, which is why the derivation never
    reaches them (next test)."""
    assert SQLiteDialect().suggested_data_types()[str] is SQLITE_DATA_TYPE_SUGGESTIONS[str]
    assert DummyDialect().suggested_data_types()[str] is DUMMY_DATA_TYPE_SUGGESTIONS[str]


def test_a_derivation_does_not_bind_the_template():
    """The copy-on-bind discipline, observed from the outside: building a
    statement binds the dialect on the suggestion it adopted, and the module's
    template is still unbound afterwards."""
    _create(BareRow)

    with pytest.raises(ValueError, match="has no dialect bound"):
        _ = SQLITE_DATA_TYPE_SUGGESTIONS[str].dialect


def test_the_extra_table_is_empty_and_disjoint():
    dialect = SQLiteDialect()
    assert dialect.suggested_extra_data_types() == {}
    assert set(dialect.suggested_data_types()).isdisjoint(
        dialect.suggested_extra_data_types()
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


def test_the_integer_concepts_are_pinned():
    """The set the derivation reads, written out: a width class a dialect gains
    without joining this set would silently fail to become an identity, and
    the derivation would never name the reason."""
    assert _INTEGER_CONCEPTS == frozenset(
        {"integer", "bigint", "smallint", "tinyint"}
    )
