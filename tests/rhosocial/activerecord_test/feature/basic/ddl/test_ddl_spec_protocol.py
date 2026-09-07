# tests/rhosocial/activerecord_test/feature/basic/ddl/test_ddl_spec_protocol.py
"""Tests for the DDL feature-spec claiming protocol (``build_spec``).

Covers the generic Spec translations on the core (SQLite / Dummy) dialects:

- ``DDLSpec`` base is a pure marker (no fields, no behavior).
- Generic Specs translate to the expected expression-layer objects.
- Lazy predicate / value factories are evaluated at build time.
- Unclaimed Specs (``PartitionSpec`` subclasses, unknown objects) return
  ``None`` (silently ignored).
- ``build_spec`` output is consumable by ``CreateTableExpression`` /
  ``CreateIndexExpression`` (the diff/migration link).
"""

import sys

import pytest

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated

from rhosocial.activerecord.base import (
    CheckSpec,
    DDLSpec,
    DefaultSpec,
    ForeignKeySpec,
    GeneratedColumnSpec,
    IndexSpec,
    JsonColumnSpec,
    NotNullSpec,
    PartialIndexSpec,
    PartitionSpec,
    PrimaryKeySpec,
    UniqueSpec,
    UseConstraint,
    UseIndex,
)
from rhosocial.activerecord.backend.expression.core import Column
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnConstraint,
    ColumnConstraintType,
    CreateTableExpression,
    ForeignKeyConstraint,
    IndexDefinition,
    TableConstraint,
    TableConstraintType,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


@pytest.fixture
def dialect():
    return SQLiteDialect()


class TestProtocolConformance:
    """Base DDLSpec is a pure marker; dialect exposes build_spec."""

    def test_ddl_spec_is_empty_marker(self):
        spec = DDLSpec()
        assert not hasattr(spec, "__dict__") or not spec.__dict__
        assert DDLSpec.__slots__ == ()

    def test_build_spec_returns_none_for_unknown(self, dialect):
        assert dialect.build_spec(object()) is None

    def test_build_spec_returns_none_for_partition_marker(self, dialect):
        # Core defines no partition classes; SQLite claims none → unpartitioned.
        assert dialect.build_spec(PartitionSpec()) is None


class TestGenericSpecTranslation:
    def test_check_spec_to_table_constraint(self, dialect):
        result = dialect.build_spec(
            CheckSpec(condition=lambda d: Column(d, "age") >= 18, name="ck_age")
        )
        assert isinstance(result, TableConstraint)
        assert result.constraint_type == TableConstraintType.CHECK
        assert result.name == "ck_age"
        assert result.check_condition is not None

    def test_check_spec_ready_predicate_passthrough(self, dialect):
        pred = Column(dialect, "age") >= 18
        result = dialect.build_spec(CheckSpec(condition=pred))
        assert result.check_condition is pred  # no factory, same object

    def test_unique_spec_to_table_constraint(self, dialect):
        result = dialect.build_spec(UniqueSpec(columns=["a", "b"], name="uq_ab"))
        assert isinstance(result, TableConstraint)
        assert result.constraint_type == TableConstraintType.UNIQUE
        assert result.columns == ["a", "b"]
        assert result.name == "uq_ab"

    def test_not_null_spec_to_column_constraint(self, dialect):
        result = dialect.build_spec(NotNullSpec(column="a"))
        assert isinstance(result, ColumnConstraint)
        assert result.constraint_type == ColumnConstraintType.NOT_NULL

    def test_primary_key_single_to_column_constraint(self, dialect):
        result = dialect.build_spec(PrimaryKeySpec(columns=["id"]))
        assert isinstance(result, ColumnConstraint)
        assert result.constraint_type == ColumnConstraintType.PRIMARY_KEY

    def test_primary_key_composite_to_table_constraint(self, dialect):
        result = dialect.build_spec(PrimaryKeySpec(columns=["a", "b"]))
        assert isinstance(result, TableConstraint)
        assert result.constraint_type == TableConstraintType.PRIMARY_KEY
        assert result.columns == ["a", "b"]

    def test_default_spec_literal(self, dialect):
        result = dialect.build_spec(DefaultSpec(column="status", value="active"))
        assert isinstance(result, ColumnConstraint)
        assert result.constraint_type == ColumnConstraintType.DEFAULT
        sql, params = result.default_value.to_sql()
        assert params == ("active",)

    def test_default_spec_rejects_raw_flag(self, dialect):
        # Raw SQL defaults are not a portable common denominator; expression
        # defaults belong in backend-specific Spec classes. The ``raw`` flag
        # was removed from ``DefaultSpec``.
        with pytest.raises(TypeError):
            DefaultSpec(column="id", value="nextval('seq')", raw=True)

    def test_default_spec_lazy_value(self, dialect):
        result = dialect.build_spec(
            DefaultSpec(column="x", value=lambda d: 42)
        )
        sql, params = result.default_value.to_sql()
        assert params == (42,)

    def test_foreign_key_spec(self, dialect):
        result = dialect.build_spec(
            ForeignKeySpec(
                ["user_id"], "users", ["id"],
                on_delete="CASCADE", on_update="RESTRICT", name="fk_user",
            )
        )
        assert isinstance(result, ForeignKeyConstraint)
        assert result.foreign_key_table == "users"
        assert result.foreign_key_columns == ["id"]
        assert result.columns == ["user_id"]
        from rhosocial.activerecord.backend.expression.statements import ReferentialAction
        assert result.on_delete == ReferentialAction.CASCADE
        assert result.on_update == ReferentialAction.RESTRICT

    def test_foreign_key_invalid_action_raises(self, dialect):
        with pytest.raises(ValueError):
            dialect.build_spec(
                ForeignKeySpec(["user_id"], "users", on_delete="BOGUS")
            )

    def test_index_spec(self, dialect):
        result = dialect.build_spec(
            IndexSpec(columns=["email"], name="ix_email", unique=True)
        )
        assert isinstance(result, IndexDefinition)
        assert result.columns == ["email"]
        assert result.unique is True

    def test_index_spec_partial(self, dialect):
        result = dialect.build_spec(
            IndexSpec(
                columns=["email"],
                name="ix_active_email",
                partial_condition=lambda d: Column(d, "is_active") == 1,
            )
        )
        assert isinstance(result, IndexDefinition)
        assert result.partial_condition is not None


class TestBuildSpecOutputConsumedByExpressions:
    """The claimed Spec output must be usable by the expression layer."""

    def test_specs_feed_create_table(self, dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            ColumnDefinition,
        )
        from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType

        pk = dialect.build_spec(PrimaryKeySpec(["id"]))
        uq = dialect.build_spec(UniqueSpec(["email"], name="uq_email"))
        ck = dialect.build_spec(
            CheckSpec(lambda d: Column(d, "age") >= 18, name="ck_age")
        )
        df = dialect.build_spec(DefaultSpec("status", "active"))
        fk = dialect.build_spec(
            ForeignKeySpec(["user_id"], "users", ["id"], on_delete="CASCADE")
        )
        idx = dialect.build_spec(IndexSpec(["email"], name="ix_email"))

        cols = [
            ColumnDefinition("id", IntegerType(), constraints=[pk]),
            ColumnDefinition("email", VarCharType(length=255)),
            ColumnDefinition("age", IntegerType()),
            ColumnDefinition("status", VarCharType(length=20), constraints=[df]),
            ColumnDefinition("user_id", IntegerType()),
        ]
        expr = CreateTableExpression(
            dialect=dialect,
            table="t_users",
            columns=cols,
            indexes=[idx],
            table_constraints=[uq, ck, fk],
        )
        sql, params = expr.to_sql()
        assert "PRIMARY KEY" in sql
        assert "UNIQUE" in sql
        assert "CHECK" in sql
        assert "DEFAULT" in sql
        assert "REFERENCES" in sql
        assert "ON DELETE CASCADE" in sql

    def test_partial_index_spec_feeds_create_index(self, dialect):
        from rhosocial.activerecord.backend.expression.statements import CreateIndexExpression

        idx = dialect.build_spec(
            IndexSpec(
                columns=["email"],
                name="ix_active_email",
                partial_condition=lambda d: Column(d, "is_active") == 1,
            )
        )
        expr = CreateIndexExpression(
            dialect=dialect,
            index="ix_active_email",
            table="users",
            columns=["email"],
            where=idx.partial_condition,
        )
        sql, _ = expr.to_sql()
        assert "WHERE" in sql


class TestDiffLink:
    """build_spec output participates in CreateTableExpression.diff."""

    def test_diff_sees_spec_built_constraints(self, dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            ColumnDefinition,
        )
        from rhosocial.activerecord.backend.expression.types import IntegerType

        def make(pk_cols, uq):
            uq_con = dialect.build_spec(UniqueSpec(uq, name="uq_email"))
            cols = [
                ColumnDefinition(c, IntegerType())
                for c in pk_cols
            ]
            return CreateTableExpression(
                dialect=dialect,
                table="t",
                columns=cols,
                table_constraints=[uq_con],
            )

        old = make(["id"], ["email"])
        new = make(["id"], ["email", "phone"])
        plan = dialect.diff_create_table(old, new)
        # composite uniqueness change should be detected
        assert plan.alters or plan.rebuild is not None


class TestModelIntegration:
    """Specs declared on ActiveRecord models flow through generate_create_table."""

    def test_model_spec_constraints_and_indexes(self, dialect):
        from rhosocial.activerecord.model import ActiveRecord

        class Order(ActiveRecord):
            __table_name__ = "orders"
            __table_constraints__ = [
                UniqueSpec(columns=["account_id", "period"], name="uq_acc_period"),
                CheckSpec(
                    condition=lambda d: Column(d, "debit_total")
                    == Column(d, "credit_total"),
                    name="ck_balance",
                ),
            ]
            __table_indexes__ = [
                IndexSpec(columns=["created_at"], name="ix_created"),
            ]
            account_id: int
            period: str
            debit_total: float
            credit_total: float
            created_at: str

        expr = Order.generate_create_table(dialect)
        sql, _ = expr.to_sql()
        assert "CONSTRAINT \"uq_acc_period\" UNIQUE" in sql
        assert "CONSTRAINT \"ck_balance\" CHECK" in sql
        assert expr.indexes[0].name == "ix_created"

    def test_model_unclaimed_partition_is_ignored(self, dialect):
        from rhosocial.activerecord.model import ActiveRecord

        class NoPartition(ActiveRecord):
            __table_name__ = "np"
            __table_partition__ = [PartitionSpec()]
            x: int

        expr = NoPartition.generate_create_table(dialect)
        assert expr.partition is None  # unclaimed → unpartitioned

    def test_model_prebuilt_expression_objects_still_work(self, dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            TableConstraint,
            TableConstraintType,
        )
        from rhosocial.activerecord.model import ActiveRecord

        class Legacy(ActiveRecord):
            __table_name__ = "legacy"
            __table_constraints__ = [
                TableConstraint(
                    constraint_type=TableConstraintType.UNIQUE,
                    columns=["a"],
                )
            ]
            a: int

        expr = Legacy.generate_create_table(dialect)
        assert len(expr.table_constraints) == 1


class TestFieldLevelLazyPredicates:
    """Field annotations may carry lazy ``(dialect) -> SQLPredicate`` factories."""

    def test_field_check_lazy(self, dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            ColumnConstraintType as CCT,
        )
        from rhosocial.activerecord.model import ActiveRecord

        class T(ActiveRecord):
            __table_name__ = "t"
            age: Annotated[
                int,
                UseConstraint(
                    CCT.CHECK,
                    check_condition=lambda d: Column(d, "age") >= 18,
                    name="ck_age",
                ),
            ]

        expr = T.generate_create_table(dialect)
        sql, params = expr.to_sql()
        assert "CHECK" in sql
        assert params == (18,)

    def test_field_index_partial_lazy(self, dialect):
        from rhosocial.activerecord.model import ActiveRecord

        class T(ActiveRecord):
            __table_name__ = "t"
            is_active: Annotated[
                int,
                UseIndex(
                    "ix_active",
                    partial_condition=lambda d: Column(d, "is_active") == 1,
                ),
            ]

        expr = T.generate_create_table(dialect)
        assert expr.indexes[0].partial_condition is not None


class TestSpecProductRouting:
    """Spec products are routed by kind, regardless of declaration slot.

    Regression: an ``IndexSpec`` / ``PartialIndexSpec`` (or a pre-built
    ``IndexDefinition``) declared in ``__table_constraints__`` used to land in
    ``table_constraints`` and break rendering ("IndexDefinition has no
    attribute constraint_type"). Index products must always go to
    ``expr.indexes``; constraint products to ``expr.table_constraints``.
    """

    def test_partial_index_spec_in_constraints_slot_routes_to_indexes(self, dialect):
        from rhosocial.activerecord.model import ActiveRecord

        class T(ActiveRecord):
            __table_name__ = "t"
            __table_constraints__ = [
                PartialIndexSpec(
                    columns=["email"],
                    condition=lambda d: Column(d, "is_active") == 1,
                    name="ix_active_email",
                ),
            ]
            email: str
            is_active: int

        expr = T.generate_create_table(dialect)
        assert [i.name for i in expr.indexes] == ["ix_active_email"]
        # The constraint list carries no index products.
        assert not any(
            isinstance(c, IndexDefinition) for c in expr.table_constraints
        )

    def test_index_spec_in_constraints_slot_routes_to_indexes(self, dialect):
        from rhosocial.activerecord.model import ActiveRecord

        class T(ActiveRecord):
            __table_name__ = "t"
            __table_constraints__ = [
                IndexSpec(columns=["email"], name="ix_email"),
            ]
            email: str

        expr = T.generate_create_table(dialect)
        assert [i.name for i in expr.indexes] == ["ix_email"]
        assert not any(
            isinstance(c, IndexDefinition) for c in expr.table_constraints
        )

    def test_prebuilt_index_definition_in_constraints_slot_routes_to_indexes(
        self, dialect
    ):
        from rhosocial.activerecord.model import ActiveRecord

        class T(ActiveRecord):
            __table_name__ = "t"
            __table_constraints__ = [
                IndexDefinition(name="ix_email", columns=["email"]),
            ]
            email: str

        expr = T.generate_create_table(dialect)
        assert [i.name for i in expr.indexes] == ["ix_email"]

    def test_check_spec_in_indexes_slot_routes_to_constraints(self, dialect):
        from rhosocial.activerecord.model import ActiveRecord

        class T(ActiveRecord):
            __table_name__ = "t"
            __table_indexes__ = [
                CheckSpec(lambda d: Column(d, "x") >= 0, name="ck_x"),
            ]
            x: int

        expr = T.generate_create_table(dialect)
        names = [c.name for c in expr.table_constraints]
        assert "ck_x" in names
        assert expr.indexes == []

    def test_regular_slotting_unchanged(self, dialect):
        from rhosocial.activerecord.model import ActiveRecord

        class T(ActiveRecord):
            __table_name__ = "t"
            __table_constraints__ = [
                UniqueSpec(["a", "b"], name="uq_ab"),
            ]
            __table_indexes__ = [
                IndexSpec(columns=["a"], name="ix_a"),
            ]
            a: int
            b: int

        expr = T.generate_create_table(dialect)
        assert [i.name for i in expr.indexes] == ["ix_a"]
        assert any(getattr(c, "name", None) == "uq_ab" for c in expr.table_constraints)
        # Routing must not duplicate products across slots.
        assert len(expr.indexes) == 1


class TestIndexToCreateIndexExpression:
    """``IndexDefinition.to_create_index_expression`` converts derived index
    definitions into executable statements (regression: IndexDefinition has
    no ``to_sql`` — rendering requires ``CreateIndexExpression``)."""

    def test_conversion_field_mapping(self, dialect):
        from rhosocial.activerecord.backend.expression.statements import (
            CreateIndexExpression,
        )

        idx = dialect.build_spec(
            IndexSpec(
                columns=["email"],
                name="ix_email",
                unique=True,
                type="BTREE",
                partial_condition=lambda d: Column(d, "is_active") == 1,
            )
        )
        expr = idx.to_create_index_expression(dialect, "users")
        assert isinstance(expr, CreateIndexExpression)
        assert expr.index == "ix_email"
        assert expr.table == "users"
        assert expr.unique is True
        assert expr.index_type == "BTREE"
        assert expr.where is not None
        sql, params = expr.to_sql()
        assert "CREATE UNIQUE INDEX" in sql
        assert "WHERE" in sql

    def test_accepts_table_expression(self, dialect):
        from rhosocial.activerecord.backend.expression.core import TableExpression

        idx = dialect.build_spec(IndexSpec(columns=["a"], name="ix_a"))
        expr = idx.to_create_index_expression(dialect, TableExpression(dialect, "t"))
        assert expr.table == "t"


class TestCapabilitySpecs:
    """Core capability Specs (partial index / JSON / generated column)."""

    def test_partial_index_spec_translation(self, dialect):
        from rhosocial.activerecord.model import ActiveRecord

        class T(ActiveRecord):
            __table_name__ = "t"
            __table_indexes__ = [
                PartialIndexSpec(
                    columns=["email"],
                    condition=lambda d: Column(d, "is_active") == 1,
                    name="ix_active_email",
                ),
            ]
            email: str
            is_active: int

        expr = T.generate_create_table(dialect)
        assert isinstance(expr.indexes[0], IndexDefinition)
        assert expr.indexes[0].partial_condition is not None

    def test_json_column_spec_translation(self, dialect):
        from rhosocial.activerecord.model import ActiveRecord

        class T(ActiveRecord):
            __table_name__ = "t"
            __table_constraints__ = [JsonColumnSpec("meta")]
            meta: object

        expr = T.generate_create_table(dialect)
        from rhosocial.activerecord.backend.expression.types import JsonType
        assert isinstance(expr.columns[0].data_type, JsonType)

    def test_generated_column_spec(self, dialect):
        from rhosocial.activerecord.model import ActiveRecord

        dialect.version = (3, 45, 0)

        class T(ActiveRecord):
            __table_name__ = "t"
            __table_constraints__ = [
                GeneratedColumnSpec(
                    "double_age",
                    expression=lambda d: Column(d, "age") * 2,
                    stored=True,
                ),
            ]
            age: int
            double_age: int

        expr = T.generate_create_table(dialect)
        col = next(c for c in expr.columns if c.name == "double_age")
        assert col.generated_expression is not None
        assert col.generated_type is not None