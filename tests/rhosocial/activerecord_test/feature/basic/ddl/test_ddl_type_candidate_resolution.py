# tests/rhosocial/activerecord_test/feature/basic/ddl/test_ddl_type_candidate_resolution.py
"""What a dialect's answer to a declared type is allowed to mean.

A field may declare several candidate types and the derivation picks the
first one the dialect can render.  That loop must distinguish two outcomes:

* the dialect **answers** -- it has no rendering for the concept, or it
  renders the concept but refuses this declaration.  The next candidate is
  tried, and if none works the caller is told no declared type is supported.
* the formatter **fails** -- a ``TypeError``, an ``AttributeError``, anything
  raised while rendering what it claims to support.  That is a defect and has
  to surface; reporting it as "unsupported" sends the reader after a
  capability that was never missing.
"""

try:  # Python 3.8 has no typing.Annotated
    from typing import Annotated, Optional
except ImportError:  # pragma: no cover - only on 3.8
    from typing import Optional

    from typing_extensions import Annotated

import pytest

from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.base.derivation import build_create_table_statement
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.types import IntegerType, UUIDType, VarCharType
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.model import ActiveRecord


class AnsweringDialect(SQLiteDialect):
    """Renders ``uuid`` only by refusing it -- a refusal is an answer."""

    def format_data_type_uuid(self, data_type):
        raise UnsupportedFeatureError(
            "AnsweringDialect", "the generic type 'uuid'", "declare something else"
        )


class CrashingDialect(SQLiteDialect):
    """Its formatter for ``integer`` is simply buggy."""

    def format_data_type_integer(self, data_type):
        raise TypeError("broken formatter: an argument is the wrong kind")


class RefusedFirst(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "refused_first"

    id: Annotated[Optional[int], UseSqlType(UUIDType(), IntegerType())] = None


class RefusedOnly(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "refused_only"

    id: Annotated[Optional[int], UseSqlType(UUIDType())] = None


class Crashing(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "crashing"

    id: Annotated[Optional[int], UseSqlType(IntegerType())] = None


class Unrendered(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "unrendered"

    token: Annotated[Optional[str], UseSqlType(UUIDType())] = None


class DeclaredPart(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "declared_part"

    id: Annotated[Optional[int], UseSqlType(IntegerType())] = None
    name: Annotated[str, UseSqlType(VarCharType(length=64))]


def test_a_refused_candidate_falls_through_to_the_next():
    """A refusal is an answer, so the loop keeps looking."""
    statement = build_create_table_statement(RefusedFirst, AnsweringDialect())

    assert "INTEGER" in statement.to_sql()[0]


def test_every_candidate_refused_says_no_declared_type_is_supported():
    with pytest.raises(
        ValueError, match="no declared type is supported by AnsweringDialect"
    ):
        build_create_table_statement(RefusedOnly, AnsweringDialect())


def test_a_formatter_that_crashes_is_not_reported_as_unsupported():
    """The one thing the loop must not do is turn a bug into a capability."""
    with pytest.raises(TypeError, match="broken formatter"):
        build_create_table_statement(Crashing, CrashingDialect())


def test_a_concept_the_dialect_does_not_render_is_an_answer():
    """SQLite has no generic ``uuid``; the model declares no alternative."""
    with pytest.raises(
        ValueError, match="no declared type is supported by SQLiteDialect"
    ):
        build_create_table_statement(Unrendered, SQLiteDialect())


def test_the_unrendered_concept_keeps_its_own_diagnosis():
    """Asked directly, the dialect still names the concept and its substitute."""
    dialect = SQLiteDialect()
    with pytest.raises(TypeError, match="does not support the generic type 'uuid'"):
        dialect.format_data_type(UUIDType())


def test_derivation_binds_a_copy_not_the_model_declaration():
    """The model's own DataType must not end up pointing at a backend.

    A DataType is a value object whose dialect is a rendering attribute. Binding
    the declared instance would leave the model carrying whichever backend
    derived it last, so a second derivation would read a stale binding.
    """
    for _ in range(2):
        build_create_table_statement(DeclaredPart, SQLiteDialect()).to_sql()

    declared = DeclaredPart.column_data_type("name")
    prototype = declared.data_type
    with pytest.raises(ValueError, match="has no dialect bound"):
        _ = prototype.dialect
