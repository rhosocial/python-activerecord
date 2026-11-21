# tests/rhosocial/activerecord_test/feature/basic/ddl/test_integer_pk_suggestion.py
"""Contracts for integer-primary-key declaration and auto-increment suggestions.

- A bare model (no ``IntegerPKMixin``) is keyless: a field annotated
  ``Optional[int]`` named ``id`` does NOT become a primary key by itself.
- ``IntegerPKMixin`` packages the id field plus the ``__primary_key__``
  declaration, and the three interface methods read that declaration.
- Integer-family detection is by class, so a backend-renamed integer type is
  recognized (the name-literal check that broke bare ids is gone).
- The DDL suggestion data class and its protocol/mixin are the backend-facing
  capability; they carry no primary key.
"""
from rhosocial.activerecord.field import IntegerPKMixin

from typing import Optional

from rhosocial.activerecord.backend.dialect.protocols import IntegerAutoIncrementColumnSuggestionSupport
from rhosocial.activerecord.backend.suggestion import IntegerAutoIncrementColumnSuggestion
from rhosocial.activerecord.backend.expression.types import IntegerType
from rhosocial.activerecord.backend.impl.sqlite.mixins import (
    SQLiteIntegerAutoIncrementColumnSuggestionMixin,
)
from rhosocial.activerecord.base.derivation import build_create_table_statement
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.model import ActiveRecord


class _Bare(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "bare"

    id: Optional[int] = None
    name: str = ""


class _WithMixin(IntegerPKMixin, ActiveRecord):
    @classmethod
    def table_name(cls):
        return "with_mixin"


class _Composite(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "composite"

    __primary_key__ = ("a", "b")
    a: int = 0
    b: int = 0


def test_bare_id_is_not_a_primary_key():
    assert _Bare.primary_key_columns() == ()
    sql, _ = build_create_table_statement(
        _Bare, SQLiteDialect(version=(3, 53, 0))
    ).to_sql()
    assert "PRIMARY KEY" not in sql


def test_integer_pk_mixin_declares_id():
    assert _WithMixin.primary_key_columns() == ("id",)
    assert "id" in _WithMixin.ddl_field_names()


def test_composite_declaration_via_dunder():
    assert _Composite.primary_key_columns() == ("a", "b")
    assert _Composite.is_composite_pk() is True


def test_bare_id_with_mixin_gets_autoincrement_on_sqlite():
    sql, _ = build_create_table_statement(
        _WithMixin, SQLiteDialect(version=(3, 53, 0))
    ).to_sql()
    assert '"id" INTEGER PRIMARY KEY AUTOINCREMENT' in sql


def test_suggestion_data_class_carries_no_primary_key():
    s = IntegerAutoIncrementColumnSuggestion(IntegerType(), None)
    assert not hasattr(s, "primary_key")
    assert s.type == IntegerType()
    assert s.auto_increment is None


def test_suggestion_protocol_and_backend_mixin_exist():
    assert issubclass(SQLiteDialect, IntegerAutoIncrementColumnSuggestionSupport)
    assert issubclass(SQLiteDialect, SQLiteIntegerAutoIncrementColumnSuggestionMixin)
    # Core ships no default implementation: a backend either implements the
    # protocol itself or has no integer auto-increment suggestion at all.
    from rhosocial.activerecord.backend.dialect import mixins as _mixins

    assert not hasattr(_mixins, "IntegerAutoIncrementColumnSuggestionMixin")


def test_sqlite_suggestion_carries_the_autoincrement_clause():
    from rhosocial.activerecord.backend.impl.sqlite.sqlite_auto_increment_clause import (
        SQLiteAutoIncrementClause,
    )

    suggestion = SQLiteDialect().suggest_integer_auto_increment_column(IntegerType())
    assert isinstance(suggestion.type, IntegerType)
    # SQLite uses a dedicated rowid-alias clause so the generic AutoIncrementClause
    # stays fail-closed on dialects whose supports_auto_increment_column() is False.
    assert isinstance(suggestion.auto_increment, SQLiteAutoIncrementClause)
