# tests/rhosocial/activerecord_test/feature/basic/ddl/test_derived_ddl.py
"""Unit tests for ActiveRecord-derived DDL (Phase 1: create/drop table).

These tests are self-contained: the model is bound to an in-memory SQLite
backend only to obtain a dialect, and assertions are made on the derived
expressions and their rendered SQL (no live database connection required).
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

try:
    from typing import Annotated
except ImportError:  # Python 3.8
    from typing_extensions import Annotated
from uuid import UUID

import pytest

from rhosocial.activerecord.base import (
    ColumnTypeResolutionError,
    ColumnTypeResolver,
    PythonTypeMapping,
    UseColumn,
    UseConstraint,
    UseIndex,
    UseSqlType,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnConstraintType,
    ColumnDefinition,
    CreateTableExpression,
)
from rhosocial.activerecord.backend.expression.types import VarCharType
from rhosocial.activerecord.base.ddl.options import ColumnOptions
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.model import ActiveRecord


class Color(Enum):
    RED = "red"
    GREEN = "green"


class Sample(ActiveRecord):
    __table_name__ = "samples"

    id: int
    name: str
    nickname: Optional[str]
    email: Annotated[str, UseIndex("idx_samples_email", unique=True)]
    balance: Optional[Decimal]
    created_at: Optional[datetime]
    code: Annotated[str, UseSqlType(VarCharType(length=10))]
    status: Annotated[Optional[str], UseConstraint(ColumnConstraintType.NOT_NULL)]


class Named(ActiveRecord):
    __table_name__ = "named"

    user_id: Annotated[int, UseColumn("id")]
    label: str


class Composite(ActiveRecord):
    __table_name__ = "composite"
    __primary_key__ = ("order_id", "product_id")

    order_id: int
    product_id: int
    quantity: int


class Unsupported(ActiveRecord):
    __table_name__ = "unsupported"

    payload: object


class Overridden(ActiveRecord):
    __table_name__ = "overridden"

    id: int
    name: str

    @classmethod
    def table_options(cls):
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            CreateTableOptions,
            TableCommentClause,
        )

        return CreateTableOptions(None, comment=TableCommentClause(None, "hello"))


class Misdeclared(ActiveRecord):
    __table_name__ = "misdeclared"

    id: int

    @classmethod
    def table_partition(cls):
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            IndexDefinition,
        )

        return IndexDefinition(None, name="idx", columns=["id"])


class FakeColumnDefinition(ColumnDefinition):
    """A stand-in for a backend-specific column definition."""

    def __init__(self, *args, extra=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra = extra


class FakeColumnOptions(ColumnOptions):
    """A stand-in for a backend-specific column options declaration."""

    def __init__(self, *, extra, **kwargs):
        super().__init__(**kwargs)
        self.extra = extra

    def column_definition_class(self):
        return FakeColumnDefinition

    def apply_to(self, column):
        column.extra = self.extra


class WithColumnOptions(ActiveRecord):
    __table_name__ = "with_column_options"

    id: int
    name: str

    @classmethod
    def column_options(cls, field):
        if field == "name":
            return FakeColumnOptions(extra="typed")
        return None


@pytest.fixture
def backend():
    instance = SQLiteBackend(SQLiteConnectionConfig(database=":memory:"))
    Sample.__backend__ = instance
    Named.__backend__ = instance
    Composite.__backend__ = instance
    Unsupported.__backend__ = instance
    WithColumnOptions.__backend__ = instance
    return instance


def test_handler_collects_field_metadata():
    assert set(Sample.__table_ddl_fields__) == set(Sample.model_fields)
    assert Sample.__table_ddl_fields__["nickname"].is_optional is True
    assert Sample.__table_ddl_fields__["name"].is_optional is False
    assert Sample.__table_ddl_fields__["code"].use_sql_type is not None


def test_python_type_mapping_basics():
    assert type(PythonTypeMapping.data_type_for(int)).__name__ == "IntegerType"
    assert type(PythonTypeMapping.data_type_for(bool)).__name__ == "BooleanType"
    assert type(PythonTypeMapping.data_type_for(datetime)).__name__ == "DateTimeType"
    assert type(PythonTypeMapping.data_type_for(date)).__name__ == "DateType"
    assert type(PythonTypeMapping.data_type_for(str)).__name__ == "TextType"
    assert PythonTypeMapping.data_type_for(object) is None


def test_create_table_returns_expression(backend):
    expression = Sample.create_table()
    assert isinstance(expression, CreateTableExpression)
    sql, params = expression.to_sql()
    assert sql.startswith('CREATE TABLE "samples" (')
    assert params == ()


def test_optional_fields_add_no_null_clause(backend):
    sql, _ = Sample.create_table().to_sql()
    # §5.7: Optional[T] is nullable — no explicit NULL clause is output.
    assert '"nickname" TEXT NULL' not in sql
    assert '"nickname" TEXT' in sql
    assert '"balance" NUMERIC NULL' not in sql


def test_required_fields_add_not_null(backend):
    sql, _ = Sample.create_table().to_sql()
    # §5.7: required T derives NOT NULL.
    assert '"name" TEXT NOT NULL' in sql


def test_pk_members_are_forced_not_null(backend):
    sql, _ = Sample.create_table().to_sql()
    # §5.7: PK members are forced NOT NULL (even the auto-increment PK).
    assert '"id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL' in sql


def test_explicit_not_null_overrides_optional(backend):
    sql, _ = Sample.create_table().to_sql()
    assert '"status" TEXT NOT NULL' in sql


def test_primary_key_auto_increment_for_integer(backend):
    sql, _ = Sample.create_table().to_sql()
    assert '"id" INTEGER PRIMARY KEY AUTOINCREMENT' in sql


def test_use_sql_type_override(backend):
    sql, _ = Sample.create_table().to_sql()
    assert '"code" TEXT' in sql


def test_inline_indexes_omitted_when_unsupported(backend):
    # SQLite has no inline index support: CREATE TABLE carries no indexes.
    assert Sample.create_table().indexes == []


def test_use_index_is_derived(backend):
    # §5.4: table_indexes() returns only table-level declarations; the
    # field-level index is collected through column_indexes().
    assert Sample.table_indexes() == []
    field_indexes = Sample.column_indexes("email")
    assert [index.name for index in field_indexes] == ["idx_samples_email"]
    assert field_indexes[0].unique is True

    statements = Sample.create_indexes()
    assert len(statements) == 1
    assert statements[0].index_name == "idx_samples_email"
    assert statements[0].unique is True


def test_use_column_maps_column_and_primary_key(backend):
    sql, _ = Named.create_table().to_sql()
    assert '"id" INTEGER PRIMARY KEY AUTOINCREMENT' in sql
    assert '"user_id"' not in sql
    assert '"label" TEXT' in sql


def test_composite_primary_key_becomes_table_constraint(backend):
    expression = Composite.create_table()
    sql, _ = expression.to_sql()
    assert 'PRIMARY KEY ("order_id", "product_id")' in sql


def test_drop_table_expression(backend):
    sql, params = Sample.drop_table(if_exists=True).to_sql()
    assert sql == 'DROP TABLE IF EXISTS "samples"'
    assert params == ()


def test_drop_table_purge_flag_is_carried(backend):
    assert Sample.drop_table(purge=True).purge is True


def test_drop_table_purge_unsupported_raises(backend):
    from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

    with pytest.raises(UnsupportedFeatureError, match="PURGE"):
        Sample.drop_table(purge=True).to_sql()


def test_spec_roundtrip(backend):
    original = Sample.create_table()
    spec = Sample.create_table_spec()
    rebuilt = Sample.create_table_from_spec(spec)
    assert rebuilt.to_sql() == original.to_sql()


def test_unsupported_python_type_raises(backend):
    with pytest.raises(ColumnTypeResolutionError):
        Unsupported.create_table()


def test_resolver_maps_canonical_types():
    resolver = ColumnTypeResolver(SQLiteDialect((3, 53, 0)))
    assert resolver.resolve(int).name == "integer"
    assert resolver.resolve(str).name == "text"
    assert resolver.resolve(UUID).name.startswith("sqlite_")
    assert resolver.is_integer(resolver.resolve(int)) is True
    assert resolver.is_integer(resolver.resolve(str)) is False


def test_resolver_instantiate_carries_parameters():
    from rhosocial.activerecord.backend.expression.types import EnumType

    resolver = ColumnTypeResolver(SQLiteDialect((3, 53, 0)))
    original = EnumType(values=["red", "green"])
    instance = resolver.instantiate(EnumType, original)
    assert instance.get_params()["values"] == ("red", "green")


def test_resolver_use_sql_type_priority():
    dialect = SQLiteDialect((3, 53, 0))
    resolver = ColumnTypeResolver(dialect)
    resolved = resolver.resolve(str, UseSqlType(VarCharType(length=10)))
    assert resolved.name == "varchar"
    assert resolved.length == 10


def test_binder_copies_declared_expression(backend):
    from rhosocial.activerecord.base.ddl import DialectBinder
    from rhosocial.activerecord.backend.expression.statements.ddl_table import (
        CreateTableOptions,
        TableCommentClause,
    )

    declared = CreateTableOptions(None, comment=TableCommentClause(None, "hello"))
    bound = DialectBinder(backend.dialect).bind(declared)

    assert bound is not declared
    assert bound.dialect is backend.dialect
    with pytest.raises(ValueError):
        _ = declared.dialect


def test_interface_override_is_used(backend):
    Overridden.__backend__ = backend
    expression = Overridden.create_table()
    assert expression.table_options is not None
    assert expression.table_options.comment.comment == "hello"


def test_gate0_rejects_misdeclared_candidate(backend):
    Misdeclared.__backend__ = backend
    with pytest.raises(TypeError):
        Misdeclared.create_table()


def test_column_options_selects_backend_definition_class(backend):
    expression = WithColumnOptions.create_table()
    name_column = next(col for col in expression.columns if col.name == "name")
    assert isinstance(name_column, FakeColumnDefinition)
    assert name_column.extra == "typed"
    id_column = next(col for col in expression.columns if col.name == "id")
    assert type(id_column) is ColumnDefinition


def test_column_options_default_definition_class_is_generic():
    assert ColumnOptions().column_definition_class() is ColumnDefinition
