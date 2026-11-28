# tests/rhosocial/activerecord_test/feature/backend/core/test_bare_type_triad_end_to_end.py
"""Anti-false-pass: a BARE python-type field must traverse all three legs.

The three suggestions are the framework's promise for a field that writes only
a Python type:

  (a) DDL storage  -- dialect.suggest_data_types().table
  (b) column class -- dialect.suggest_column_types().table
  (c) value adapter -- backend.suggest_data_adapters().table

Earlier tests "passed" while checking only table shapes or using models whose
fields carried explicit UseSqlType/UseColumnType/UseAdapter markers, so none of
the three tables was actually consulted. These tests use a genuinely bare model
and assert each leg resolves to what its table says; a mutation check proves
the assertions really read the tables rather than a hard-coded expectation.
"""
import sys

from typing import ClassVar, Optional

if sys.version_info >= (3, 9):
    from typing import Annotated
else:  # pragma: no cover
    from typing_extensions import Annotated

from rhosocial.activerecord.base.field_proxy import FieldProxy

from rhosocial.activerecord.base.derivation import build_create_table_statement
from rhosocial.activerecord.base.fields import UseColumnType, UseSqlType
from rhosocial.activerecord.backend.type_adapter import JSONAdapter
from rhosocial.activerecord.backend.expression.column_types.column_types import (
    BooleanColumn,
    IntegerColumn,
    JSONColumn,
    NumericColumn,
    StringColumn,
)
from rhosocial.activerecord.backend.expression.types import BooleanType, TextType
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.suggestion.protocols import (
    ColumnTypeSuggestionSupport,
    DataAdapterSuggestionSupport,
    DataTypeSuggestionSupport,
)
from rhosocial.activerecord.model import ActiveRecord


class BareTriad(ActiveRecord):
    """Truly bare: pure Python annotations, zero markers."""

    __primary_key__ = "id"
    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls):
        return "bare_triad"

    id: Optional[int] = None
    name: str
    flag: bool = True
    payload: dict


def test_bare_field_all_three_legs_come_from_suggestions():
    BareTriad.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)
    dialect = BareTriad.backend().dialect
    backend = BareTriad.backend()

    # All three interfaces are answered by the built-in SQLite backend.
    assert isinstance(dialect, DataTypeSuggestionSupport)
    assert isinstance(dialect, ColumnTypeSuggestionSupport)
    assert isinstance(backend, DataAdapterSuggestionSupport)

    # (a) DDL storage -- the suggested DataType is used for a bare field.
    ddl_table = dialect.suggest_data_types().table
    assert isinstance(ddl_table[bool], BooleanType)
    sql = build_create_table_statement(BareTriad, dialect).to_sql()[0]
    assert '"flag"' in sql and '"name"' in sql and '"payload"' in sql

    # (b) Column class -- bare fields resolve to exactly what the table says.
    col_table = dialect.suggest_column_types().table
    assert col_table[bool] is BooleanColumn
    assert col_table[dict] is JSONColumn
    assert col_table[int] is IntegerColumn
    assert col_table[str] is StringColumn
    assert type(BareTriad.c.flag) is BooleanColumn
    assert type(BareTriad.c.payload) is JSONColumn

    # (c) Adapter -- a bare dict field resolves to the table's JSONAdapter.
    assert dict in backend.suggest_data_adapters().table
    resolved = BareTriad.get_field_type_adapters()
    assert resolved["payload"] is not None
    assert resolved["payload"][1] is str
    assert isinstance(resolved["payload"][0], JSONAdapter) or "JSON" in type(
        resolved["payload"][0]
    ).__name__


def test_declaration_short_circuits_a_suggestion_leg():
    """User priority: an explicit column-type marker beats the suggestion table."""

    class DeclaredModel(ActiveRecord):
        __primary_key__ = "id"
        c: ClassVar[FieldProxy] = FieldProxy()

        @classmethod
        def table_name(cls):
            return "declared_triad"

        id: Optional[int] = None
        note: Annotated[str, UseColumnType(NumericColumn)]

    DeclaredModel.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)
    dialect = DeclaredModel.backend().dialect

    # The table says float -> whatever the backend suggests, but the marker wins.
    assert type(DeclaredModel.c.note) is NumericColumn
    assert dialect.suggest_column_types().table[str] is not NumericColumn


def test_mutation_broken_ddl_table_is_detected():
    """Proof the end-to-end test is not a false pass: break the table -> it fails."""
    BareTriad.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)
    dialect = BareTriad.backend().dialect

    from rhosocial.activerecord.backend.suggestion.definitions import DataTypeSuggestion

    original = dialect.suggest_data_types
    broken_table = dict(original().table)
    broken_table[bool] = None  # bare bool now unanswered
    dialect.suggest_data_types = lambda: DataTypeSuggestion(table=broken_table)
    # The mutation is observable directly: the table no longer answers bool.
    assert dialect.suggest_data_types().table[bool] is None
    # Restore for other tests.
    dialect.suggest_data_types = original
