# tests/rhosocial/activerecord_test/feature/basic/ddl/test_generate_ddl.py
"""
Project-specific tests for the DDL generation system (Phase 1 + Phase 2).

Covers:
- Table-level declarations: TableOptions, __table_indexes__, __table_constraints__
- Field-level declarations: UseSqlType, UseIndex, UseConstraint
- ModelSchemaGenerator: type resolution, PK, auto-increment, composite PK
- ActiveRecord.generate_create_table(): returns expression INSTANCE (not SQL)
- Cross-backend type suggestion via ColumnTypeSuggestion protocol
"""

import datetime
import decimal
import uuid
import sys
if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated
from typing import Optional

import pytest

from rhosocial.activerecord.backend.config import ConnectionConfig
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnConstraintType,
    CreateTableExpression,
    DropTableExpression,
    TableConstraint,
    TableConstraintType,
)
from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    BlobType,
    BooleanType,
    CharType,
    CustomType,
    DateType,
    DateTimeType,
    DecimalType,
    DoubleType,
    FloatType,
    IntType,
    IntegerType,
    IntervalType,
    JsonBType,
    JsonType,
    RealType,
    SmallIntType,
    TextType,
    TimeType,
    TimeTzType,
    TimestampType,
    TimestampTzType,
    VarCharType,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.backend.sync import SQLiteBackend
from rhosocial.activerecord.base import (
    ColumnConstraintType as CCT,
    IndexDefinition,
    ModelSchemaGenerator,
    TableOptions,
    UseConstraint,
    UseIndex,
    UseSqlType,
)
from rhosocial.activerecord.model import ActiveRecord


# ---------------------------------------------------------------------------
# Minimal model for table-level + field-level tests (no backend configured)
# ---------------------------------------------------------------------------

class _Article(ActiveRecord):
    __table_name__ = "articles"
    __table_options__ = TableOptions(
        charset="utf8mb4", collation="utf8mb4_unicode_ci", engine="InnoDB"
    )
    __table_indexes__ = [
        IndexDefinition(name="idx_title_status", columns=["title", "status"]),
        IndexDefinition(name="uq_slug", columns=["slug"], unique=True),
    ]
    __table_constraints__ = [
        TableConstraint(
            name="uq_title_author",
            constraint_type=TableConstraintType.UNIQUE,
            columns=["title", "author"],
        ),
    ]

    id: int
    title: Annotated[str, UseSqlType(VarCharType(length=255))]
    slug: Annotated[str, UseIndex("idx_slug")]
    status: Annotated[str, UseConstraint(CCT.COLLATE, collation="utf8mb4_bin")]
    author: str
    body: Optional[str] = None


# ---------------------------------------------------------------------------
# Table-level declaration tests
# ---------------------------------------------------------------------------

class TestTableLevelDeclarations:

    def test_table_options_stored(self):
        opts = _Article.__ddl_table_options__
        assert opts.charset == "utf8mb4"
        assert opts.collation == "utf8mb4_unicode_ci"
        assert opts.engine == "InnoDB"
        assert opts.has_options()

    def test_empty_table_options(self):
        assert not TableOptions().has_options()

    def test_composite_indexes_collected(self):
        names = {i.name for i in _Article.__ddl_indexes__}
        assert {"idx_title_status", "uq_slug", "idx_slug"} == names

    def test_composite_constraints_collected(self):
        cs = _Article.__ddl_constraints__
        assert len(cs) == 1
        assert cs[0].constraint_type == TableConstraintType.UNIQUE
        assert cs[0].columns == ["title", "author"]


# ---------------------------------------------------------------------------
# Field-level declaration tests
# ---------------------------------------------------------------------------

class TestFieldLevelDeclarations:

    def test_use_sql_type_single(self):
        u = _Article.__table_field_sql_types__["title"]
        assert u.data_type == VarCharType(length=255)

    def test_use_sql_type_dict_form_rejected(self):
        """Per-dialect string-keyed mappings are no longer supported."""
        with pytest.raises(TypeError, match="DataType instances"):
            UseSqlType({"postgres": JsonBType(), "default": TextType()})

    def test_use_sql_type_non_datatype_rejected(self):
        with pytest.raises(TypeError, match="DataType instances"):
            UseSqlType("VARCHAR(255)")

    def test_use_sql_type_empty_rejected(self):
        with pytest.raises(TypeError, match="at least one DataType"):
            UseSqlType()

    def test_use_sql_type_multiple_and_dedupe(self):
        u = UseSqlType(JsonType(), JsonType(), TextType())
        assert [type(t).__name__ for t in u.data_types] == ["JsonType", "TextType"]
        assert type(u.data_type).__name__ == "JsonType"

    def test_use_index_to_index_definition(self):
        idxs = _Article.__table_field_indexes__["slug"]
        assert len(idxs) == 1
        assert idxs[0].name == "idx_slug"
        assert idxs[0].columns == ["slug"]

    def test_use_constraint_collate(self):
        cs = _Article.__table_field_constraints__["status"]
        assert len(cs) == 1
        assert cs[0].constraint_type == CCT.COLLATE
        assert cs[0].collation == "utf8mb4_bin"

    def test_use_constraint_character_set(self):
        marker = UseConstraint(CCT.CHARACTER_SET, character_set="utf8mb4")
        assert marker.constraint.constraint_type == CCT.CHARACTER_SET
        assert marker.constraint.character_set == "utf8mb4"


# ---------------------------------------------------------------------------
# ModelSchemaGenerator tests (uses DummyDialect — no backend needed)
# ---------------------------------------------------------------------------

class TestModelSchemaGenerator:

    def test_generate_returns_expression_instance(self):
        expr = ModelSchemaGenerator.generate_create_table(_Article, DummyDialect())
        assert isinstance(expr, CreateTableExpression)

    def test_column_count_and_order(self):
        expr = ModelSchemaGenerator.generate_create_table(_Article, DummyDialect())
        names = [c.name for c in expr.columns]
        assert names == ["id", "title", "slug", "status", "author", "body"]

    def test_type_resolution_use_sql_type(self):
        expr = ModelSchemaGenerator.generate_create_table(_Article, DummyDialect())
        title_col = next(c for c in expr.columns if c.name == "title")
        assert isinstance(title_col.data_type, VarCharType)

    def test_type_resolution_suggestion(self):
        class _Simple(ActiveRecord):
            name: str
            count: int
            flag: bool
            ts: datetime.datetime
            amount: decimal.Decimal

        expr = ModelSchemaGenerator.generate_create_table(_Simple, DummyDialect())
        types = {c.name: type(c.data_type) for c in expr.columns}
        assert types["name"] is TextType
        assert types["count"] is IntegerType
        assert types["flag"] is BooleanType
        assert types["ts"] is DateTimeType
        assert types["amount"] is DecimalType

    def test_optional_type_resolution(self):
        class _Opt(ActiveRecord):
            bio: Optional[str] = None
        expr = ModelSchemaGenerator.generate_create_table(_Opt, DummyDialect())
        assert isinstance(expr.columns[0].data_type, TextType)

    def test_single_pk_auto_increment(self):
        class _Auto(ActiveRecord):
            id: int
            name: str
        expr = ModelSchemaGenerator.generate_create_table(_Auto, DummyDialect())
        pk_col = next(c for c in expr.columns if c.name == "id")
        pk = [c for c in pk_col.constraints if c.constraint_type == ColumnConstraintType.PRIMARY_KEY]
        assert len(pk) == 1
        assert pk[0].is_auto_increment is True

    def test_non_integer_pk_no_auto_increment(self):
        class _StrPK(ActiveRecord):
            __primary_key__ = "slug"
            slug: str
        expr = ModelSchemaGenerator.generate_create_table(_StrPK, DummyDialect())
        pk_col = next(c for c in expr.columns if c.name == "slug")
        pk = [c for c in pk_col.constraints if c.constraint_type == ColumnConstraintType.PRIMARY_KEY]
        assert len(pk) == 1
        assert pk[0].is_auto_increment is False

    def test_composite_pk_table_constraint(self):
        class _OrderItem(ActiveRecord):
            __table_name__ = "order_items"
            __primary_key__ = ("order_id", "product_id")
            order_id: int
            product_id: int
            qty: int

        expr = ModelSchemaGenerator.generate_create_table(_OrderItem, DummyDialect())
        pks = [c for c in expr.table_constraints
               if c.constraint_type == TableConstraintType.PRIMARY_KEY]
        assert len(pks) == 1
        assert pks[0].columns == ["order_id", "product_id"]
        # Single-column PK constraint should NOT be added to columns
        for col in expr.columns:
            assert not any(
                c.constraint_type == ColumnConstraintType.PRIMARY_KEY
                for c in col.constraints
            )

    def test_table_options_propagated(self):
        expr = ModelSchemaGenerator.generate_create_table(_Article, DummyDialect())
        assert expr.table_options is not None
        assert expr.table_options.charset == "utf8mb4"

    def test_indexes_propagated(self):
        expr = ModelSchemaGenerator.generate_create_table(_Article, DummyDialect())
        names = {i.name for i in expr.indexes}
        assert "idx_title_status" in names
        assert "idx_slug" in names

    def test_constraints_propagated(self):
        expr = ModelSchemaGenerator.generate_create_table(_Article, DummyDialect())
        uqs = [c for c in expr.table_constraints if c.constraint_type == TableConstraintType.UNIQUE]
        assert any(u.columns == ["title", "author"] for u in uqs)

    def test_if_not_exists_flag(self):
        expr = ModelSchemaGenerator.generate_create_table(_Article, DummyDialect(), if_not_exists=True)
        assert expr.if_not_exists is True

    def test_temporary_flag(self):
        expr = ModelSchemaGenerator.generate_create_table(_Article, DummyDialect(), temporary=True)
        assert expr.temporary is True

    def test_single_instance_applies_directly(self):
        """UseSqlType carries the exact DataType instance, applied as-is."""
        class _Override(ActiveRecord):
            data: Annotated[dict, UseSqlType(JsonType())]

        expr = ModelSchemaGenerator.generate_create_table(_Override, DummyDialect())
        assert isinstance(expr.columns[0].data_type, JsonType)


class TestGeneratorEdgeCases:
    """Type-resolution fallbacks and validation branches."""

    def test_marker_validation_branches(self):
        """UseColumn / UseAdapter / UseIndex construction guards."""
        from rhosocial.activerecord.base.fields import UseAdapter, UseColumn, UseIndex

        with pytest.raises(TypeError, match="column_name"):
            UseColumn(123)
        with pytest.raises(ValueError, match="Column name cannot be empty"):
            UseColumn("   ")
        with pytest.raises(TypeError, match="SQLTypeAdapter"):
            UseAdapter("not-an-adapter", str)
        with pytest.raises(ValueError, match="non-empty index name"):
            UseIndex("")

    def test_unresolvable_annotations_fall_back_to_integer(self):
        """object / List[int] / Optional[Union[int, str]] cannot be unwrapped to
        a concrete python type -> neutral fallback to IntegerType."""
        from typing import List, Optional, Union

        class _Edge(ActiveRecord):
            a: object
            b: List[int]
            c: Optional[Union[int, str]]

        expr = ModelSchemaGenerator.generate_create_table(_Edge, DummyDialect())
        for col in expr.columns:
            assert isinstance(col.data_type, IntegerType)

    def test_non_integer_auto_pk_degrades(self):
        """__pk_auto_generated__ on a non-int PK drops the auto-increment flag."""
        class _StrPKAuto(ActiveRecord):
            __primary_key__ = "slug"
            __pk_auto_generated__ = True
            slug: str

        expr = ModelSchemaGenerator.generate_create_table(_StrPKAuto, DummyDialect())
        pk_col = next(c for c in expr.columns if c.name == "slug")
        pk = [c for c in pk_col.constraints if c.constraint_type == ColumnConstraintType.PRIMARY_KEY]
        assert len(pk) == 1
        assert pk[0].is_auto_increment is False

    def test_invalid_table_options_rejected(self):
        class _Bad(ActiveRecord):
            __table_options__ = "invalid"
            id: int

        with pytest.raises(TypeError, match="TableOptions"):
            ModelSchemaGenerator.generate_create_table(_Bad, DummyDialect())


# ---------------------------------------------------------------------------
# ActiveRecord.generate_create_table() integration tests
# ---------------------------------------------------------------------------

class TestGenerateDdlApi:

    def test_returns_expression_instance(self):
        _Article.configure(ConnectionConfig(database=":memory:"), SQLiteBackend)
        expr = _Article.generate_create_table()
        assert isinstance(expr, CreateTableExpression)

    def test_dialect_override(self):
        expr = _Article.generate_create_table(DummyDialect())
        assert isinstance(expr, CreateTableExpression)
        assert expr.dialect is not None

    def test_if_not_exists_passed_through(self):
        _Article.configure(ConnectionConfig(database=":memory:"), SQLiteBackend)
        expr = _Article.generate_create_table(if_not_exists=True)
        assert expr.if_not_exists is True

    def test_user_calls_to_sql_themselves(self):
        """The API returns an expression; the user decides to call to_sql()."""
        _Article.configure(ConnectionConfig(database=":memory:"), SQLiteBackend)
        expr = _Article.generate_create_table()
        sql, params = expr.to_sql()
        assert "CREATE TABLE" in sql.upper()
        assert "articles" in sql.lower()

    def test_async_model_has_ddl_api(self):
        from rhosocial.activerecord.model import AsyncActiveRecord
        assert hasattr(AsyncActiveRecord, "generate_create_table")
        assert hasattr(AsyncActiveRecord, "generate_drop_table")

    def test_generate_drop_table_returns_expression_instance(self):
        _Article.configure(ConnectionConfig(database=":memory:"), SQLiteBackend)
        expr = _Article.generate_drop_table()
        assert isinstance(expr, DropTableExpression)

    def test_generate_drop_table_to_sql(self):
        _Article.configure(ConnectionConfig(database=":memory:"), SQLiteBackend)
        sql, params = _Article.generate_drop_table(if_exists=True).to_sql()
        assert "DROP TABLE" in sql.upper()
        assert "IF EXISTS" in sql.upper()
        assert "articles" in sql.lower()
        assert params == ()


# ---------------------------------------------------------------------------
# ColumnTypeSuggestion protocol tests
# ---------------------------------------------------------------------------

class TestColumnTypeSuggestion:

    def test_dummy_satisfies_protocol(self):
        from rhosocial.activerecord.backend.dialect.protocols import ColumnTypeSuggestion
        assert isinstance(DummyDialect(), ColumnTypeSuggestion)

    def test_sqlite_satisfies_protocol(self):
        from rhosocial.activerecord.backend.dialect.protocols import ColumnTypeSuggestion
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
        assert isinstance(SQLiteDialect(), ColumnTypeSuggestion)

    @pytest.mark.parametrize("py_type,expected_type", [
        (str, TextType),
        (int, IntegerType),
        (bool, BooleanType),
        (float, DoubleType),
        (bytes, BlobType),
        (datetime.datetime, DateTimeType),
        (datetime.date, DateType),
        (decimal.Decimal, DecimalType),
        (uuid.UUID, VarCharType),
        (dict, TextType),
        (list, TextType),
    ])
    def test_neutral_suggestions(self, py_type, expected_type):
        d = DummyDialect()
        result = d.suggest_column_type(py_type)
        assert result is not None
        assert isinstance(result, expected_type)

    def test_unknown_type_returns_none(self):
        assert DummyDialect().suggest_column_type(object) is None


# ---------------------------------------------------------------------------
# UnsupportedFeatureError degradation contract
# ---------------------------------------------------------------------------

class TestDegradationContract:

    def test_unsupported_feature_error_is_exception(self):
        assert issubclass(UnsupportedFeatureError, Exception)

    def test_generator_never_silences(self):
        """The generator produces the expression as-declared; if a feature is
        unsupported, to_sql() raises — the generator does not drop it."""
        _Article.configure(ConnectionConfig(database=":memory:"), SQLiteBackend)
        expr = _Article.generate_create_table()
        # Expression carries all declared features regardless of backend support
        assert len(expr.indexes) >= 2
        assert len(expr.table_constraints) >= 1


# ---------------------------------------------------------------------------
# Type vocabulary: generic default rendering / backend-specific ownership
# ---------------------------------------------------------------------------

class TestTypeVocabulary:

    def test_generic_types_render_standard_sql_by_default(self):
        """Generic core types render SQL-standard forms via the base mixin's
        defaults, even for a backend with no overrides (portable-by-construction)."""
        from rhosocial.activerecord.backend.dialect.mixins.ddl_type import DDLTypeMixin

        class _BareDialect(DDLTypeMixin):
            pass

        d = _BareDialect()
        assert d.format_data_type(IntegerType()) == ("INTEGER", ())
        assert d.format_data_type(IntType()) == ("INTEGER", ())
        assert d.format_data_type(SmallIntType()) == ("SMALLINT", ())
        assert d.format_data_type(BigIntType()) == ("BIGINT", ())
        assert d.format_data_type(FloatType()) == ("FLOAT", ())
        assert d.format_data_type(FloatType(precision=24)) == ("FLOAT(24)", ())
        assert d.format_data_type(RealType()) == ("REAL", ())
        assert d.format_data_type(DoubleType()) == ("DOUBLE PRECISION", ())
        assert d.format_data_type(DecimalType()) == ("DECIMAL", ())
        assert d.format_data_type(DecimalType(precision=10)) == ("DECIMAL(10)", ())
        assert d.format_data_type(DecimalType(precision=10, scale=2)) == (
            "DECIMAL(10, 2)", ())
        assert d.format_data_type(BooleanType()) == ("BOOLEAN", ())
        assert d.format_data_type(CharType()) == ("CHAR", ())
        assert d.format_data_type(CharType(length=10)) == ("CHAR(10)", ())
        assert d.format_data_type(VarCharType(length=50)) == ("VARCHAR(50)", ())
        assert d.format_data_type(TextType()) == ("TEXT", ())
        assert d.format_data_type(BlobType()) == ("BLOB", ())
        assert d.format_data_type(DateType()) == ("DATE", ())
        assert d.format_data_type(TimeType()) == ("TIME", ())
        assert d.format_data_type(TimeType(precision=3)) == ("TIME(3)", ())
        assert d.format_data_type(DateTimeType()) == ("TIMESTAMP", ())
        assert d.format_data_type(DateTimeType(precision=3)) == ("TIMESTAMP(3)", ())
        assert d.format_data_type(TimestampType()) == ("TIMESTAMP", ())
        assert d.format_data_type(JsonType()) == ("JSON", ())

    def test_supports_data_types_enumerates_base_defaults(self):
        """supports_data_types() lists the portable generic types on a bare
        dialect (auto-generated from the base default formatters)."""
        from rhosocial.activerecord.backend.dialect.mixins.ddl_type import DDLTypeMixin

        class _BareDialect(DDLTypeMixin):
            pass

        supported = dict(_BareDialect().supports_data_types())
        assert supported[IntegerType] == "INTEGER"
        assert supported[VarCharType] == "VARCHAR"
        assert supported[JsonType] == "JSON"
        assert supported[BooleanType] == "BOOLEAN"
        assert BigIntType in supported

    def test_custom_type_requires_explicit_registration(self):
        """CustomType has no base default: backends must opt in, otherwise render
        raises (raw SQL passthrough is a security-sensitive escape hatch)."""
        from rhosocial.activerecord.backend.dialect.mixins.ddl_type import DDLTypeMixin

        class _BareDialect(DDLTypeMixin):
            pass

        with pytest.raises(TypeError, match="no formatter"):
            _BareDialect().format_data_type(CustomType(raw="GEOMETRY"))

    def test_sqlite_does_not_silently_substitute_specific_types(self):
        """SQLite no longer maps tz/JSONB types to lossy NUMERIC/TEXT."""
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
        dialect = SQLiteDialect()
        for specific in (JsonBType(), TimestampTzType(), TimeTzType(), IntervalType()):
            with pytest.raises(TypeError, match="no formatter"):
                dialect.format_data_type(specific)

    def test_sqlite_still_renders_generic_types(self):
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
        dialect = SQLiteDialect()
        assert dialect.format_data_type(IntegerType()) == ("INTEGER", ())
        assert dialect.format_data_type(JsonType()) == ("TEXT", ())
        assert dialect.format_data_type(VarCharType(length=50)) == ("TEXT", ())

    def test_backend_specific_subclass_not_absorbed(self):
        """A backend-specific subclass of a generic type must be registered on
        a backend to render there; other backends raise (anti-absorption)."""
        from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
        dialect = DummyDialect()
        fake_mysql_type = type("MySQLXmlType", (VarCharType,), {})
        with pytest.raises(TypeError, match="no formatter"):
            dialect.format_data_type(fake_mysql_type())
        assert dialect.supports_data_type(VarCharType) is True
        assert dialect.supports_data_type(fake_mysql_type) is False

    def test_supports_data_type(self):
        from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
        dialect = DummyDialect()
        assert dialect.supports_data_type(IntegerType()) is True
        assert dialect.supports_data_type(JsonBType()) is True  # dummy renders faithfully
        assert dialect.supports_data_type(TimeTzType()) is True

    def test_custom_type_raw_passthrough(self):
        """CustomType.raw is emitted verbatim — hardcoded trusted strings only."""
        from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
        dialect = DummyDialect()
        assert dialect.format_data_type(CustomType(raw="geometry(Point,4326)")) == (
            "geometry(Point,4326)", ())


# ---------------------------------------------------------------------------
# Multi-type UseSqlType: first-renderable selection / fallback / error
# ---------------------------------------------------------------------------

class TestMultiTypeSelection:

    def _generate(self, model, dialect):
        return ModelSchemaGenerator.generate_create_table(model, dialect)

    def test_first_renderable_type_selected(self):
        """JsonBType (postgres-only) is skipped on sqlite; JsonType wins."""
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        class _M(ActiveRecord):
            payload: Annotated[dict, UseSqlType(JsonBType(), JsonType())]

        expr = self._generate(_M, SQLiteDialect())
        assert isinstance(expr.columns[0].data_type, JsonType)

    def test_declaration_order_is_priority(self):
        """When both are renderable, the first declared type wins."""
        from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

        class _A(ActiveRecord):
            payload: Annotated[dict, UseSqlType(JsonType(), TextType())]

        class _B(ActiveRecord):
            payload: Annotated[dict, UseSqlType(TextType(), JsonType())]

        expr_a = self._generate(_A, DummyDialect())
        expr_b = self._generate(_B, DummyDialect())
        assert isinstance(expr_a.columns[0].data_type, JsonType)
        assert isinstance(expr_b.columns[0].data_type, TextType)

    def test_none_renderable_falls_back_to_suggestion(self):
        """JsonBType (postgres-only) on sqlite -> suggest(dict -> TextType)."""
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        class _M(ActiveRecord):
            payload: Annotated[dict, UseSqlType(JsonBType())]

        expr = self._generate(_M, SQLiteDialect())
        assert isinstance(expr.columns[0].data_type, TextType)

    def test_none_renderable_and_no_suggestion_raises(self):
        """A dialect with no suggestion and no renderable declared type errors."""
        from rhosocial.activerecord.backend.dialect.mixins.ddl_type import DDLTypeMixin

        class _BareDialect(DDLTypeMixin):
            pass

        class _M(ActiveRecord):
            payload: Annotated[dict, UseSqlType(JsonBType())]

        with pytest.raises(TypeError, match="none of the declared UseSqlType"):
            self._generate(_M, _BareDialect())

    def test_multiple_use_sql_type_markers_rejected(self):
        """Two Annotated UseSqlType markers on one field is ambiguous -> error."""
        with pytest.raises(TypeError, match="multiple UseSqlType markers"):
            class _M(ActiveRecord):
                payload: Annotated[
                    dict, UseSqlType(JsonType()), UseSqlType(TextType()),
                ]
