# tests/rhosocial/activerecord_test/feature/basic/ddl/test_soft_delete_partial_unique.py
"""The recipe: a soft-deleted table's business key is a partial unique index.

Zero new API -- this pins how two existing declarations compose, so the
combination cannot silently stop working. ``UseIndex(partial_condition=...)``
supplies the ``WHERE deleted_at IS NULL`` predicate and ``SoftDeleteMixin``
supplies the column it names.
"""
from typing import ClassVar, Optional

from rhosocial.activerecord.backend.expression import Column, IsNullPredicate
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.base import FieldProxy, UseIndex
from rhosocial.activerecord.field import DefaultSoftDeleteMixin
from rhosocial.activerecord.model import ActiveRecord

try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

import pytest


class SoftDeletedEmail(DefaultSoftDeleteMixin, ActiveRecord):
    """One row per address, but only among the rows that are not deleted."""

    @classmethod
    def table_name(cls):
        return "soft_delete_partial_unique"

    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    email: Annotated[
        str,
        UseIndex(
            "uq_soft_delete_partial_unique_email",
            unique=True,
            partial_condition=lambda dialect: IsNullPredicate(
                dialect, Column(dialect, "deleted_at")
            ),
        ),
    ]
    label: str = ""


def _resolved_index(dialect):
    """The declared index with its lazy condition resolved, as DDL would."""
    marker = SoftDeletedEmail.__table_ddl_fields__["email"].indexes[0]
    definition = SoftDeletedEmail.index_definition(marker, "email")
    condition = definition.partial_condition
    if callable(condition):
        condition = condition(dialect)
    return definition, condition


class TestIndexDeclaration:
    def test_partial_condition_is_carried(self):
        definition, _ = _resolved_index(SQLiteDialect())
        assert definition.unique is True
        assert definition.partial_condition is not None

    def test_condition_names_the_soft_delete_column(self):
        # The marker carries a factory, not a rendered expression: no
        # dialect exists when the class body runs. Resolving it here is what
        # the DDL generator does at build time.
        _, condition = _resolved_index(SQLiteDialect())
        rendered, params = condition.to_sql()
        assert "deleted_at" in rendered
        assert "IS NULL" in rendered.upper()

    def test_soft_delete_column_is_the_declared_locator(self):
        # The recipe is only correct while both halves name the same column.
        assert SoftDeletedEmail.deleted_at_field() == "deleted_at"


class TestRoundTrip:
    @pytest.fixture
    def table(self, tmp_path):
        SoftDeletedEmail.configure(
            SQLiteConnectionConfig(database=str(tmp_path / "partial.db")), SQLiteBackend
        )
        backend = SoftDeletedEmail.backend()
        backend.execute(
            'CREATE TABLE "soft_delete_partial_unique" ('
            '"id" INTEGER PRIMARY KEY AUTOINCREMENT, '
            '"email" TEXT NOT NULL, '
            '"label" TEXT NOT NULL DEFAULT \'\', '
            '"deleted_at" TEXT)'
        )
        definition, condition = _resolved_index(backend.dialect)
        condition_sql, condition_params = condition.to_sql()
        backend.execute(
            'CREATE UNIQUE INDEX "uq_soft_delete_partial_unique_email" '
            'ON "soft_delete_partial_unique" ("email") '
            f"WHERE {condition_sql}",
            condition_params,
        )
        return SoftDeletedEmail

    def test_live_row_then_soft_delete_then_reuse(self, table):
        first = table(email="a@example.com", label="first")
        first.save()
        first.delete()  # soft delete: the row stays, deleted_at is set

        second = table(email="a@example.com", label="second")
        second.save()  # allowed: the older row is no longer live
        assert second.id is not None
        assert table.query().where(table.c.label == "second").one().email == "a@example.com"

    def test_two_live_rows_with_one_address_are_refused(self, table):
        from rhosocial.activerecord.backend.errors import DatabaseError

        table(email="b@example.com", label="one").save()
        with pytest.raises(DatabaseError):
            table(email="b@example.com", label="two").save()
