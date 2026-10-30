# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_declared_field_contract.py
# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_declared_field_contract.py
"""Fields a formatter reads are declared on the node it formats.

Every one of these pins a case where the formatter used to ask an object
whether it carried an attribute instead of reading a declared field: the
answer was a silent default whenever the field was missing, and the feature
was unreachable when nothing ever set the attribute.
"""

import pytest

from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.mixins import AliasableMixin
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression.statements.dml import (
    InsertStatement,
    OnConflictClause,
    ValuesSource,
)


class TestDeclaredAlias:
    """``alias`` is a field of every aliased expression, not a later attachment."""

    def test_mixin_declares_alias_so_formatters_can_read_it_directly(self, dummy_dialect):
        assert AliasableMixin.alias is None
        assert Column(dummy_dialect, "name").alias is None

    def test_as_sets_the_declared_field(self, dummy_dialect):
        assert Column(dummy_dialect, "name").as_("n").alias == "n"

    def test_a_catalogue_entry_still_carries_no_alias(self, dummy_dialect):
        """The declaration lives on the aliasing mixin, not on every node."""
        assert not hasattr(Table(dummy_dialect, "users"), "alias")


class TestDeclaredInsertModifiers:
    """SQLite's OR REPLACE / OR IGNORE are fields on the node, not attributes."""

    def _values_source(self, dummy_dialect):
        return ValuesSource(dummy_dialect, [[Literal(dummy_dialect, 1)]])

    def test_defaults_are_false(self, dummy_dialect):
        stmt = InsertStatement(
            dummy_dialect, Table(dummy_dialect, "users"), self._values_source(dummy_dialect)
        )
        assert (stmt.or_replace, stmt.or_ignore) == (False, False)

    def test_or_replace_renders(self, dummy_dialect):
        sqlite = SQLiteDialect()
        stmt = InsertStatement(
            sqlite,
            Table(sqlite, "users"),
            self._values_source(sqlite),
            or_replace=True,
        )
        assert stmt.to_sql()[0].startswith("INSERT OR REPLACE INTO")

    def test_or_ignore_renders(self, dummy_dialect):
        sqlite = SQLiteDialect()
        stmt = InsertStatement(
            sqlite,
            Table(sqlite, "users"),
            self._values_source(sqlite),
            or_ignore=True,
        )
        assert stmt.to_sql()[0].startswith("INSERT OR IGNORE INTO")

    def test_a_dialect_that_spells_neither_ignores_the_modifiers(self, dummy_dialect):
        """The core spelling is unaffected: the fields default to False."""
        stmt = InsertStatement(
            dummy_dialect,
            Table(dummy_dialect, "users"),
            self._values_source(dummy_dialect),
            or_ignore=True,
        )
        assert stmt.to_sql()[0].startswith("INSERT INTO")

    def test_the_two_modifiers_are_mutually_exclusive(self, dummy_dialect):
        with pytest.raises(ValueError, match="both"):
            InsertStatement(
                dummy_dialect,
                Table(dummy_dialect, "users"),
                self._values_source(dummy_dialect),
                or_replace=True,
                or_ignore=True,
            )

    def test_the_modifiers_exclude_on_conflict(self, dummy_dialect):
        with pytest.raises(ValueError, match="on_conflict"):
            InsertStatement(
                dummy_dialect,
                Table(dummy_dialect, "users"),
                self._values_source(dummy_dialect),
                or_ignore=True,
                on_conflict=OnConflictClause(dummy_dialect, ["id"], do_nothing=True),
            )