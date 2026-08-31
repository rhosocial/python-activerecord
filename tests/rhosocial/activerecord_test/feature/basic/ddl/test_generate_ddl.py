# tests/rhosocial/activerecord_test/feature/basic/ddl/test_generate_ddl.py
"""
Project-specific tests for the DDL generation system (Phase 1 + Phase 2).

Covers:
- Table-level declarations: TableOptions, __indexes__, __constraints__
- Field-level declarations: UseSqlType, UseIndex, UseConstraint
- ModelSchemaGenerator: type resolution, PK, auto-increment, composite PK
- ActiveRecord.generate_ddl(): returns expression INSTANCE (not SQL)
- Cross-backend type suggestion via ColumnTypeSuggestion protocol
"""

import datetime
import decimal
import uuid
from typing import Annotated, Optional

import pytest

from rhosocial.activerecord.backend.config import ConnectionConfig
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnConstraintType,
    CreateTableExpression,
    TableConstraint,
    TableConstraintType,
)
from rhosocial.activerecord.backend.expression.types import (
    BlobType,
    BooleanType,
    DateType,
    DateTimeType,
    DecimalType,
    DoubleType,
    IntegerType,
    JsonBType,
    JsonType,
    TextType,
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
    __indexes__ = [
        IndexDefinition(name="idx_title_status", columns=["title", "status"]),
        IndexDefinition(name="uq_slug", columns=["slug"], unique=True),
    ]
    __constraints__ = [
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
        u = _Article.__ddl_field_sql_types__["title"]
        assert u.data_type == VarCharType(length=255)
        assert u.resolve("sqlite") == VarCharType(length=255)

    def test_use_sql_type_per_dialect(self):
        class _M(ActiveRecord):
            meta: Annotated[dict, UseSqlType({
                "postgres": JsonBType(), "mysql": JsonType(), "default": TextType(),
            })]
        u = _M.__ddl_field_sql_types__["meta"]
        assert u.resolve("postgres") == JsonBType()
        assert u.resolve("mysql") == JsonType()
        assert u.resolve("sqlite") == TextType()

    def test_use_sql_type_missing_default_raises(self):
        with pytest.raises(ValueError, match="default"):
            UseSqlType({"postgres": JsonBType()})

    def test_use_index_to_index_definition(self):
        idxs = _Article.__ddl_field_indexes__["slug"]
        assert len(idxs) == 1
        assert idxs[0].name == "idx_slug"
        assert idxs[0].columns == ["slug"]

    def test_use_constraint_collate(self):
        cs = _Article.__ddl_field_constraints__["status"]
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
        expr = ModelSchemaGenerator.generate(_Article, DummyDialect())
        assert isinstance(expr, CreateTableExpression)

    def test_column_count_and_order(self):
        expr = ModelSchemaGenerator.generate(_Article, DummyDialect())
        names = [c.name for c in expr.columns]
        assert names == ["id", "title", "slug", "status", "author", "body"]

    def test_type_resolution_use_sql_type(self):
        expr = ModelSchemaGenerator.generate(_Article, DummyDialect())
        title_col = next(c for c in expr.columns if c.name == "title")
        assert isinstance(title_col.data_type, VarCharType)

    def test_type_resolution_suggestion(self):
        class _Simple(ActiveRecord):
            name: str
            count: int
            flag: bool
            ts: datetime.datetime
            amount: decimal.Decimal

        expr = ModelSchemaGenerator.generate(_Simple, DummyDialect())
        types = {c.name: type(c.data_type) for c in expr.columns}
        assert types["name"] is TextType
        assert types["count"] is IntegerType
        assert types["flag"] is BooleanType
        assert types["ts"] is DateTimeType
        assert types["amount"] is DecimalType

    def test_optional_type_resolution(self):
        class _Opt(ActiveRecord):
            bio: Optional[str] = None
        expr = ModelSchemaGenerator.generate(_Opt, DummyDialect())
        assert isinstance(expr.columns[0].data_type, TextType)

    def test_single_pk_auto_increment(self):
        class _Auto(ActiveRecord):
            id: int
            name: str
        expr = ModelSchemaGenerator.generate(_Auto, DummyDialect())
        pk_col = next(c for c in expr.columns if c.name == "id")
        pk = [c for c in pk_col.constraints if c.constraint_type == ColumnConstraintType.PRIMARY_KEY]
        assert len(pk) == 1
        assert pk[0].is_auto_increment is True

    def test_non_integer_pk_no_auto_increment(self):
        class _StrPK(ActiveRecord):
            __primary_key__ = "slug"
            slug: str
        expr = ModelSchemaGenerator.generate(_StrPK, DummyDialect())
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

        expr = ModelSchemaGenerator.generate(_OrderItem, DummyDialect())
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
        expr = ModelSchemaGenerator.generate(_Article, DummyDialect())
        assert expr.table_options is not None
        assert expr.table_options.charset == "utf8mb4"

    def test_indexes_propagated(self):
        expr = ModelSchemaGenerator.generate(_Article, DummyDialect())
        names = {i.name for i in expr.indexes}
        assert "idx_title_status" in names
        assert "idx_slug" in names

    def test_constraints_propagated(self):
        expr = ModelSchemaGenerator.generate(_Article, DummyDialect())
        uqs = [c for c in expr.table_constraints if c.constraint_type == TableConstraintType.UNIQUE]
        assert any(u.columns == ["title", "author"] for u in uqs)

    def test_if_not_exists_flag(self):
        expr = ModelSchemaGenerator.generate(_Article, DummyDialect(), if_not_exists=True)
        assert expr.if_not_exists is True

    def test_temporary_flag(self):
        expr = ModelSchemaGenerator.generate(_Article, DummyDialect(), temporary=True)
        assert expr.temporary is True

    def test_per_dialect_type_override(self):
        """UseSqlType per-dialect wins over dialect suggestion."""
        class _Override(ActiveRecord):
            data: Annotated[dict, UseSqlType({
                "dummy": JsonType(), "default": TextType(),
            })]
        # DummyDialect.name == "Dummy" — resolver is case-insensitive
        expr = ModelSchemaGenerator.generate(_Override, DummyDialect())
        assert isinstance(expr.columns[0].data_type, JsonType)


# ---------------------------------------------------------------------------
# ActiveRecord.generate_ddl() integration tests
# ---------------------------------------------------------------------------

class TestGenerateDdlApi:

    def test_returns_expression_instance(self):
        _Article.configure(ConnectionConfig(database=":memory:"), SQLiteBackend)
        expr = _Article.generate_ddl()
        assert isinstance(expr, CreateTableExpression)

    def test_dialect_override(self):
        expr = _Article.generate_ddl(DummyDialect())
        assert isinstance(expr, CreateTableExpression)
        assert expr.dialect is not None

    def test_if_not_exists_passed_through(self):
        _Article.configure(ConnectionConfig(database=":memory:"), SQLiteBackend)
        expr = _Article.generate_ddl(if_not_exists=True)
        assert expr.if_not_exists is True

    def test_user_calls_to_sql_themselves(self):
        """The API returns an expression; the user decides to call to_sql()."""
        _Article.configure(ConnectionConfig(database=":memory:"), SQLiteBackend)
        expr = _Article.generate_ddl()
        sql, params = expr.to_sql()
        assert "CREATE TABLE" in sql.upper()
        assert "articles" in sql.lower()

    def test_async_model_has_generate_ddl(self):
        from rhosocial.activerecord.model import AsyncActiveRecord
        assert hasattr(AsyncActiveRecord, "generate_ddl")


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
        expr = _Article.generate_ddl()
        # Expression carries all declared features regardless of backend support
        assert len(expr.indexes) >= 2
        assert len(expr.table_constraints) >= 1
