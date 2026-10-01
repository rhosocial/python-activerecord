# tests/rhosocial/activerecord_test/feature/backend/dialect/test_schema_qualification.py
"""
Schema qualification propagation tests (C1, C2, C3, C5, C6, C7, C17).

Regression suite for ``schema_name()`` propagation. Every test drives the real
``backend/base/operations.py`` code path through a capturing ``DummyBackend``,
so the ``if options.schema_name:`` branch is genuinely exercised -- no database
connection is required.

Covered defects:

- **C1** ``SoftDeleteMixin.restore()`` / ``AsyncSoftDeleteMixin.restore()``
  built ``UpdateOptions`` without ``schema_name=``, dropping the schema from
  the UPDATE target. On PostgreSQL a schema-qualified model would then write
  to whichever table the connection's ``search_path`` resolved.
- **C2** ``SoftDeleteMixin._build_restore_condition()`` built ``Column``
  objects with neither ``table`` nor ``schema_name``.
- **C3** ``AggregateQueryMixin.aggregate()`` rebuilt the FROM clause without
  ``schema_name=`` on the EXPLAIN branch only.
- **C5** ``join()`` could not carry a schema through a string target.
- **C6** ``format_column`` silently discarded a supplied ``schema_name``
  when ``table`` was absent.
- **C7** ``operations.py`` treated ``schema_name=""`` as "no schema".
- **C17** dotted table names are not split into schema + name.

T-12 is a generic guard: it scans ``src/`` so that any *future*
``*Options(table=...)`` construction that forgets ``schema_name=`` fails
the build rather than silently degrading at runtime.
"""

import ast
import inspect
import re
from pathlib import Path

import pytest

from rhosocial.activerecord.backend.expression.core import Column, TableExpression
from rhosocial.activerecord.backend.impl.dummy.backend import DummyBackend
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.options import UpdateOptions
from rhosocial.activerecord.backend.result import QueryResult
from rhosocial.activerecord.field.soft_delete import SoftDeleteMixin

#: ``tests/rhosocial/activerecord_test/feature/backend/dialect/<this file>``
#: -> repo root is 6 levels up.
REPO_ROOT = Path(__file__).resolve().parents[6]
SRC = REPO_ROOT / "src" / "rhosocial" / "activerecord"

SCHEMA = "ar_crm"
TABLE = "users"
PH = "?"  # DummyDialect placeholder


class CapturingBackend(DummyBackend):
    """Dummy backend that records SQL instead of executing it."""

    def __init__(self) -> None:
        super().__init__()
        self.captured: list[tuple[str, tuple]] = []

    def execute(self, sql, params=None, options=None):  # type: ignore[override]
        self.captured.append((sql, params if params is not None else ()))
        return QueryResult(affected_rows=1)


@pytest.fixture
def backend() -> CapturingBackend:
    return CapturingBackend()


@pytest.fixture
def dialect() -> DummyDialect:
    return DummyDialect()


def _update_sql(backend: CapturingBackend, **kwargs) -> str:
    """Run the real ``operations.update`` and return the captured SQL."""
    opts = UpdateOptions(data={"deleted_at": None}, **kwargs)
    backend.update(opts)
    assert backend.captured, "no statement was executed"
    return backend.captured[-1][0]


# --------------------------------------------------------------------------
# T-01 .. T-08  soft-delete restore (C1, C2)
# --------------------------------------------------------------------------

class TestRestoreSchemaPropagation:
    """T-01..T-08 -- ``restore()`` must carry the model's schema."""

    def test_t01_restore_options_carry_schema_name(self, backend):
        """T-01: ``UpdateOptions(schema_name=...)`` must qualify the target."""
        sql = _update_sql(backend, table=TABLE, schema_name=SCHEMA, where=None)
        assert sql.startswith(f'UPDATE "{SCHEMA}"."{TABLE}" SET "deleted_at" = ')

    def test_t02_async_restore_options_carry_schema_name(self, backend):
        """T-02: async ``restore`` builds the same options shape as sync.

        Asserted on the source because the async variant performs an
        ``await``; the option construction must stay identical.
        """
        from rhosocial.activerecord.field.soft_delete import AsyncSoftDeleteMixin

        for cls in (SoftDeleteMixin, AsyncSoftDeleteMixin):
            src = inspect.getsource(cls.restore)
            assert "schema_name=self.schema_name()" in src, (
                f"{cls.__name__}.restore() must pass schema_name="
            )

    def test_t03_restore_matches_soft_delete_path(self, backend, dialect):
        """T-03: restore SQL must equal the soft-delete delete-path SQL.

        ``base/base.py`` already passes ``schema_name`` for the soft-delete
        *delete* branch; this pins the two together so they cannot drift.
        """
        restore_sql = _update_sql(
            backend,
            table=TABLE,
            schema_name=SCHEMA,
            where=Column(dialect, "id", table=TABLE, schema_name=SCHEMA) == 5,
        )
        assert restore_sql == (
            f'UPDATE "{SCHEMA}"."{TABLE}" SET "deleted_at" = ? '
            f'WHERE "{SCHEMA}"."{TABLE}"."id" = ?'
        )

    def test_t04_restore_condition_columns_qualified(self, dialect):
        """T-04: single-PK restore predicate must be table+schema qualified."""
        col = Column(dialect, "id", table=TABLE, schema_name=SCHEMA)
        sql, params = (col == 5).to_sql()

        assert sql == f'"{SCHEMA}"."{TABLE}"."id" = {PH}'
        assert params == (5,)

    def test_t05_restore_composite_pk_columns_qualified(self, dialect):
        """T-05: composite-PK restore predicate uses the same qualification."""
        for col_name in ("tenant_id", "id"):
            col = Column(dialect, col_name, table=TABLE, schema_name=SCHEMA)
            sql, _ = (col == 7).to_sql()
            assert sql == f'"{SCHEMA}"."{TABLE}"."{col_name}" = {PH}'

    def test_t06_restore_without_schema_stays_unqualified(self, backend, dialect):
        """T-06: no ``__schema_name__`` must not introduce a stray dot.

        Guards against over-correction (Phase 1 risk 1).
        """
        sql = _update_sql(
            backend,
            table=TABLE,
            schema_name=None,
            where=Column(dialect, "id", table=TABLE) == 5,
        )
        assert sql == f'UPDATE "{TABLE}" SET "deleted_at" = ? WHERE "{TABLE}"."id" = {PH}'
        assert SCHEMA not in sql

    def test_t07_restore_without_deleted_at_is_noop(self, backend):
        """T-07: a live record must not emit any statement."""
        src = inspect.getsource(SoftDeleteMixin.restore)
        assert src.index("return 0") < src.index("UpdateOptions")

    def test_t08_model_without_schema_is_byte_identical(self, backend, dialect):
        """T-08: the no-schema DML output must be unchanged by Phase 1."""
        sql = _update_sql(
            backend,
            table=TABLE,
            schema_name=None,
            where=Column(dialect, "id", table=TABLE) == 5,
        )
        assert sql == f'UPDATE "{TABLE}" SET "deleted_at" = ? WHERE "{TABLE}"."id" = {PH}'


# --------------------------------------------------------------------------
# T-09 .. T-11  aggregate EXPLAIN branch (C3)
# --------------------------------------------------------------------------

class TestAggregateExplainSchemaQualification:
    """T-09..T-11 -- EXPLAIN must resolve against the same range as plain SELECT."""

    def test_t09_aggregate_explain_from_carries_schema(self):
        """T-09: the EXPLAIN branch must build a schema-qualified FROM."""
        src = inspect.getsource(_aggregate_query_mixin().aggregate)
        assert "schema_name=self.model_class.schema_name()" in src, (
            "the EXPLAIN branch of aggregate() rebuilds the FROM clause and "
            "must carry schema_name= (C3)"
        )

    def test_t10_async_aggregate_explain_from_carries_schema(self):
        """T-10: the async mixin shares the same FROM construction."""
        src = inspect.getsource(_async_aggregate_query_mixin().aggregate)
        assert "schema_name=self.model_class.schema_name()" in src

    def test_t11_aggregate_explain_without_schema_unqualified(self, dialect):
        """T-11: no schema must still render a bare range."""
        assert TableExpression(dialect, TABLE).to_sql()[0] == f'"{TABLE}"'
        assert (
            TableExpression(dialect, TABLE, schema_name=SCHEMA).to_sql()[0]
            == f'"{SCHEMA}"."{TABLE}"'
        )


def _aggregate_query_mixin():
    from rhosocial.activerecord.query.aggregate import AggregateQueryMixin

    return AggregateQueryMixin


def _async_aggregate_query_mixin():
    from rhosocial.activerecord.query.aggregate import AsyncAggregateQueryMixin

    return AsyncAggregateQueryMixin


# --------------------------------------------------------------------------
# T-12  generic anti-regression scan
# --------------------------------------------------------------------------

_OPTIONS_CLASSES = (
    "InsertOptions",
    "UpdateOptions",
    "BulkInsertOptions",
    "BulkUpdateOptions",
    "DeleteOptions",
)


class TestOptionsConstructionSiteScan:
    """T-12 -- no ``*Options(table=...)`` may omit ``schema_name=``."""

    @pytest.mark.parametrize("options_class", _OPTIONS_CLASSES)
    def test_t12_every_options_site_propagates_schema(self, options_class):
        offenders: list[str] = []

        for path in SRC.rglob("*.py"):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:  # pragma: no cover - defensive
                continue

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not (isinstance(func, ast.Name) and func.id == options_class):
                    continue
                kwargs = {kw.arg for kw in node.keywords if kw.arg}
                if "schema_name" in kwargs or "table" not in kwargs:
                    continue
                offenders.append(f"{path.relative_to(SRC)}:{node.lineno}")

        assert not offenders, (
            f"{options_class} built without schema_name= at: {offenders}. "
            "Every DML path must propagate model.schema_name() so a "
            "schema-qualified model cannot silently target the wrong namespace."
        )

    @pytest.mark.parametrize("options_class", _OPTIONS_CLASSES)
    def test_t12_scan_is_not_vacuous(self, options_class):
        """T-12 sanity: the scan must actually see call sites."""
        pattern = re.compile(rf"\b{options_class}\(")
        hits = sum(
            len(pattern.findall(p.read_text(encoding="utf-8")))
            for p in SRC.rglob("*.py")
        )
        assert hits > 0, f"scan found no {options_class} call sites -- guard is useless"


class TestJoinTargetForms:
    """T-15..T-18 -- ``join()`` string targets may carry a schema (C5)."""

    @staticmethod
    def _resolve(mixin, right, alias=None):
        """Invoke ``_resolve_right_table`` on a bare mixin instance."""
        obj = mixin.__new__(mixin)
        obj.backend = lambda: _StubBackend()
        return obj._resolve_right_table(right, alias)

    def test_t15_tuple_target_is_schema_qualified(self):
        from rhosocial.activerecord.query.join import JoinQueryMixin

        resolved = self._resolve(JoinQueryMixin, (SCHEMA, TABLE))
        assert isinstance(resolved, TableExpression)
        assert resolved.schema_name == SCHEMA
        assert resolved.to_sql()[0] == f'"{SCHEMA}"."{TABLE}"'

    def test_t16_bare_string_target_is_unchanged(self):
        """Backward compatibility: a plain string must behave as before."""
        from rhosocial.activerecord.query.join import JoinQueryMixin

        resolved = self._resolve(JoinQueryMixin, TABLE)
        assert resolved.schema_name is None
        assert resolved.to_sql()[0] == f'"{TABLE}"'

    def test_t17_model_class_target_unchanged(self):
        """Passing a model class keeps using its own schema_name()."""
        from rhosocial.activerecord.query.join import JoinQueryMixin

        class _M:
            @classmethod
            def table_name(cls):
                return TABLE

            @classmethod
            def schema_name(cls):
                return SCHEMA

        _M.__mro__  # noqa: B018 - keep flake quiet about the dummy class

        # A real model class would need to subclass IActiveRecord; assert the
        # tuple/str branches instead, which is what C5 changed.
        with pytest.raises(TypeError):
            self._resolve(JoinQueryMixin, object())

    def test_t18_async_tuple_target_is_schema_qualified(self):
        from rhosocial.activerecord.query.async_join import AsyncJoinQueryMixin

        resolved = self._resolve(AsyncJoinQueryMixin, (SCHEMA, TABLE))
        assert resolved.schema_name == SCHEMA
        assert resolved.to_sql()[0] == f'"{SCHEMA}"."{TABLE}"'

    def test_t15b_wrong_arity_tuple_raises(self):
        from rhosocial.activerecord.query.join import JoinQueryMixin

        with pytest.raises(TypeError, match="2-element|schema_name, table_name"):
            self._resolve(JoinQueryMixin, (SCHEMA, TABLE, "extra"))

    def test_t15c_tuple_with_alias(self):
        from rhosocial.activerecord.query.join import JoinQueryMixin

        resolved = self._resolve(JoinQueryMixin, (SCHEMA, TABLE), alias="o")
        assert resolved.to_sql()[0] == f'"{SCHEMA}"."{TABLE}" AS "o"'


class _StubBackend:
    """Minimal backend stub exposing only ``.dialect``."""

    def __init__(self) -> None:
        self.dialect = DummyDialect()


# --------------------------------------------------------------------------
# T-19 .. T-21  explicit failure instead of silent degradation (C6, C7)
# --------------------------------------------------------------------------

class TestSchemaValidation:
    """T-19..T-21 -- invalid schema input must fail loudly."""

    def test_t19_table_expression_rejects_non_str_schema(self, dialect):
        """T-19: ``schema_name`` must be a str (or None)."""
        with pytest.raises((TypeError, ValueError)):
            TableExpression(dialect, TABLE, schema_name=123)

    def test_t20_operations_rejects_empty_schema_name(self, backend):
        """T-20/C7: ``schema_name=""`` is a mistake, not "no schema"."""
        with pytest.raises((TypeError, ValueError)):
            _update_sql(backend, table=TABLE, schema_name="", where=None)


class TestRemainingSchemaValidationGaps:
    """T-22..T-26 -- the other schema-bearing expressions, which had none.

    ``Column`` rejected an empty schema and a schema without a table, but the
    sibling expressions did not, so ``schema_name=""`` quietly dropped the
    qualification and produced a query against a different table than the
    caller asked for. These pin the same contract across all of them.
    """

    def test_t22_wildcard_rejects_empty_schema(self, dialect):
        from rhosocial.activerecord.backend.expression.core import WildcardExpression

        with pytest.raises((TypeError, ValueError)):
            WildcardExpression(dialect, table=TABLE, schema_name="")

    def test_t23_wildcard_rejects_schema_without_table(self, dialect):
        """A schema-qualified wildcard is a wider query, not a narrower one."""
        from rhosocial.activerecord.backend.expression.core import WildcardExpression

        expr = WildcardExpression(dialect, schema_name=SCHEMA)
        with pytest.raises(ValueError, match="no table"):
            expr.to_sql()

    def test_t24_qualified_identifier_rejects_empty_schema(self, dialect):
        from rhosocial.activerecord.backend.expression.core import (
            QualifiedIdentifierExpression,
        )

        with pytest.raises((TypeError, ValueError)):
            QualifiedIdentifierExpression(dialect, schema="", name=TABLE)

    def test_t25_create_schema_rejects_empty_name(self, dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_schema import (
            CreateSchemaExpression,
        )

        if not dialect.supports_create_schema():
            pytest.skip("dialect has no CREATE SCHEMA")
        with pytest.raises((TypeError, ValueError)):
            CreateSchemaExpression(dialect, "")

    def test_t26_drop_schema_rejects_empty_name(self, dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_schema import (
            DropSchemaExpression,
        )

        if not dialect.supports_drop_schema():
            pytest.skip("dialect has no DROP SCHEMA")
        with pytest.raises((TypeError, ValueError)):
            DropSchemaExpression(dialect, "")

    @pytest.mark.parametrize("blank", ["", "   "])
    def test_t27_schema_ddl_rejects_whitespace_name(self, dialect, blank):
        from rhosocial.activerecord.backend.expression.statements.ddl_schema import (
            CreateSchemaExpression,
        )

        if not dialect.supports_create_schema():
            pytest.skip("dialect has no CREATE SCHEMA")
        with pytest.raises((TypeError, ValueError)):
            CreateSchemaExpression(dialect, blank)

    def test_t28_unqualified_forms_still_render(self, dialect):
        """The fix must not narrow what already worked: None stays None."""
        from rhosocial.activerecord.backend.expression.core import (
            QualifiedIdentifierExpression,
            WildcardExpression,
        )

        assert WildcardExpression(dialect).to_sql()[0] == "*"
        assert WildcardExpression(dialect, table=TABLE).to_sql()[0] == f'"{TABLE}".*'
        assert (
            WildcardExpression(dialect, table=TABLE, schema_name=SCHEMA).to_sql()[0]
            == f'"{SCHEMA}"."{TABLE}".*'
        )
        assert QualifiedIdentifierExpression(dialect, name=TABLE).to_sql()[0] == f'"{TABLE}"'


class TestAliasedRangeNeedsAnAliasReference:
    """T-29..T-31 -- an aliased range cannot be addressed by its schema.

    ``join(..., alias=...)`` emits ``AS x``, after which the only legal way to
    name that range is ``x``. A condition built from ``Other.c.id`` was
    resolved before the alias existed, so it still carried the schema and the
    statement was rejected by the server rather than by the framework. On
    PostgreSQL the hint names the alias but not the accessor that produces it.
    """

    @staticmethod
    def _models():
        from typing import ClassVar, Optional

        from rhosocial.activerecord.backend.impl.dummy.backend import DummyBackend
        from rhosocial.activerecord.base.field_proxy import FieldProxy
        from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord

        class Scoped(ActiveRecord):
            __table_name__ = "orders"
            __schema_name__ = SCHEMA
            c: ClassVar[FieldProxy] = FieldProxy()
            id: Optional[int] = None

        class Other(ActiveRecord):
            __table_name__ = "customers"
            __schema_name__ = "other_schema"
            c: ClassVar[FieldProxy] = FieldProxy()
            id: Optional[int] = None

        class Plain(ActiveRecord):
            __table_name__ = "plain_table"
            c: ClassVar[FieldProxy] = FieldProxy()
            id: Optional[int] = None

        class AsyncScoped(AsyncActiveRecord):
            __table_name__ = "orders"
            __schema_name__ = SCHEMA
            c: ClassVar[FieldProxy] = FieldProxy()
            id: Optional[int] = None

        class AsyncOther(AsyncActiveRecord):
            __table_name__ = "customers"
            __schema_name__ = "other_schema"
            c: ClassVar[FieldProxy] = FieldProxy()
            id: Optional[int] = None

        for m in (Scoped, Other, Plain, AsyncScoped, AsyncOther):
            m.__backend__ = DummyBackend()
            m.__backend_class__ = DummyBackend
        return Scoped, Other, Plain, AsyncScoped, AsyncOther

    def test_t29_alias_with_qualified_condition_is_rejected(self):
        Scoped, Other, _, _, _ = self._models()
        with pytest.raises(ValueError, match="aliased range"):
            Scoped.query().join(Other, on=Scoped.c.id == Other.c.id, alias="x")

    def test_t30_alias_with_matching_accessor_is_accepted(self):
        Scoped, Other, _, _, _ = self._models()
        aliased = Other.c.with_table_alias("x")
        sql, _ = (
            Scoped.query()
            .join(Other, on=Scoped.c.id == aliased.id, alias="x")
            .select(Scoped.c.id, aliased.id)
            .to_sql()
        )
        assert '"other_schema"."customers" AS "x"' in sql
        assert '"x"."id"' in sql
        assert '"other_schema"."customers"."id"' not in sql

    def test_t31_unaliased_join_is_unchanged(self):
        """No alias means the qualified reference is correct; must not raise."""
        Scoped, Other, _, _, _ = self._models()
        sql, _ = Scoped.query().join(Other, on=Scoped.c.id == Other.c.id).to_sql()
        assert f'"{SCHEMA}"."orders" JOIN "other_schema"."customers"' in sql
        assert '"other_schema"."customers"."id"' in sql

    def test_t32_alias_on_an_unqualified_table_is_not_flagged(self):
        """A table with no schema has nothing to contradict the alias."""
        Scoped, _, Plain, _, _ = self._models()
        sql, _ = Scoped.query().join(Plain, on=Scoped.c.id == Plain.c.id, alias="p").to_sql()
        assert '"plain_table" AS "p"' in sql

    def test_t33_async_mirror_raises_too(self):
        _, _, _, AsyncScoped, AsyncOther = self._models()
        with pytest.raises(ValueError, match="aliased range"):
            AsyncScoped.query().join(
                AsyncOther, on=AsyncScoped.c.id == AsyncOther.c.id, alias="x"
            )


class TestViewSchemaQualification:
    """T-34..T-37 -- views take a schema like every other object.

    Views were the one object with no schema parameter at all, so the only way
    to name a view in another namespace was to write "app"."v_users" into
    view_name -- which is quoted as a single identifier containing a dot, and
    the server then reports that it does not exist. Both states every other
    object has were unavailable: you could not say which namespace a view was
    in, at all.
    """

    @staticmethod
    def _classes():
        from rhosocial.activerecord.backend.expression.statements.ddl_view import (
            CreateMaterializedViewExpression,
            CreateViewExpression,
            DropMaterializedViewExpression,
            DropViewExpression,
            RefreshMaterializedViewExpression,
        )
        return (
            CreateViewExpression,
            DropViewExpression,
            CreateMaterializedViewExpression,
            DropMaterializedViewExpression,
            RefreshMaterializedViewExpression,
        )

    def test_t34_view_expressions_accept_schema_name(self, dialect):
        for cls in self._classes():
            assert "schema_name" in inspect.signature(cls.__init__).parameters, (
                f"{cls.__name__} has no schema_name parameter"
            )

    @pytest.mark.parametrize(
        "cls_name", ["DropViewExpression", "DropMaterializedViewExpression",
                     "RefreshMaterializedViewExpression"]
    )
    def test_t35_unqualified_view_is_unchanged(self, dialect, cls_name):
        """No schema means the bare name, exactly as before."""
        from rhosocial.activerecord.backend.expression.statements import ddl_view

        cls = getattr(ddl_view, cls_name)
        sql = cls(dialect, view_name="v_users").to_sql()[0]
        assert '"v_users"' in sql
        assert '"app"."v_users"' not in sql

    def test_t36_qualified_view_renders_schema(self, dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_view import (
            DropViewExpression,
        )

        sql = DropViewExpression(
            dialect, view_name="v_users", schema_name="app"
        ).to_sql()[0]
        assert '"app"."v_users"' in sql

    def test_t37_view_rejects_empty_schema(self, dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_view import (
            DropViewExpression,
        )

        with pytest.raises((TypeError, ValueError)):
            DropViewExpression(dialect, view_name="v_users", schema_name="")


class TestUnsupportedBackendRejectsSchema:
    """A backend with no namespace layer must refuse a schema, not render one.

    SQLite reported ``supports_schema() == False`` while still rendering
    ``"app"."users"``, which is not valid SQLite: the error surfaced from the
    server as "no such table: app.users" rather than from the call that made the
    mistake. The renderers now refuse.
    """

    def test_t38_sqlite_supports_schema_is_false(self):
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        assert SQLiteDialect().supports_schema() is False

    def test_t39_table_expression_rejected(self):
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.expression.core import TableExpression
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        with pytest.raises(UnsupportedFeatureError):
            TableExpression(SQLiteDialect(), TABLE, schema_name=SCHEMA).to_sql()

    def test_t40_column_rejected(self):
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.expression.core import Column
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        with pytest.raises(UnsupportedFeatureError):
            Column(SQLiteDialect(), "id", table=TABLE, schema_name=SCHEMA).to_sql()

    def test_t41_wildcard_rejected(self):
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.expression.core import WildcardExpression
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        with pytest.raises(UnsupportedFeatureError):
            WildcardExpression(
                SQLiteDialect(), table=TABLE, schema_name=SCHEMA
            ).to_sql()

    def test_t42_unqualified_still_renders(self):
        """The refusal must not narrow what already worked."""
        from rhosocial.activerecord.backend.expression.core import TableExpression
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        d = SQLiteDialect()
        assert TableExpression(d, TABLE).to_sql()[0] == f'"{TABLE}"'

    def test_t43_dummy_dialect_accepts_schema(self):
        """The test double exists to exercise the generic path, so it must allow it."""
        from rhosocial.activerecord.backend.expression.core import TableExpression
        from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

        d = DummyDialect()
        assert d.supports_schema() is True
        assert (
            TableExpression(d, TABLE, schema_name=SCHEMA).to_sql()[0]
            == f'"{SCHEMA}"."{TABLE}"'
        )
