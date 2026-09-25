# tests/rhosocial/activerecord_test/feature/basic/ddl/test_ddl_declaration_interfaces.py
"""Unit tests for the DDL declaration surfaces and interface contracts.

Covers the final design decisions of
``.claude/plan/2026-09-21/ar-ddl-declaration-and-interface-review.md``:

- §5.1  marker candidate types are restricted (and mutually exclusive);
- §5.2  the primary key has a single source, ``UseConstraint`` rejects it;
- §5.3  identity / collation ride the column-attribute channel;
- §5.4  table-level / field-level separation, merged and deduped by name;
- §5.6  candidate selection is never silent;
- §5.7  nullability rules;
- §5.9  field-level primitives and ``columns_*(fields=None)`` batch access;
- §5.12/§5.14  statement-family candidates and the parameter contract;
- expression-level DDL generation without execution.
"""

from typing import Optional

try:
    from typing import Annotated
except ImportError:  # Python 3.8
    from typing_extensions import Annotated

import pytest

from rhosocial.activerecord.base import (
    CharacterSetAttribute,
    CollationAttribute,
    ColumnAttribute,
    IdentityAttribute,
    UseColumnAttributes,
    UseConstraint,
    UseIndex,
    UseSqlType,
)
from rhosocial.activerecord.ddl import StatementContractError, StatementParamSchema, TableDDLDeriver
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.core import Column
from rhosocial.activerecord.backend.expression.statements.ddl_partition import (
    PartitionClause,
    PartitionStrategy,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnConstraintType,
    CreateTableExpression,
    IndexDefinition,
    TableConstraint,
    TableConstraintType,
)
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.model import ActiveRecord


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class WithAttributes(ActiveRecord):
    __table_name__ = "with_attributes"

    id: int
    name: Annotated[str, UseColumnAttributes(CollationAttribute(name="NOCASE"))]
    seq: Annotated[
        int,
        UseColumnAttributes(IdentityAttribute(generation="ALWAYS", start=10, increment=2)),
    ]
    charset: Annotated[str, UseColumnAttributes(CharacterSetAttribute(name="utf8mb4"))]


class CompositeWithIndex(ActiveRecord):
    __table_name__ = "composite_with_index"
    __primary_key__ = ("order_id", "product_id")
    __table_indexes__ = [
        IndexDefinition(None, name="idx_pair", columns=["order_id", "product_id"]),
    ]

    order_id: int
    product_id: Annotated[int, UseIndex("idx_pair")]
    quantity: int


class WithTableConstraints(ActiveRecord):
    __table_name__ = "with_table_constraints"
    __table_constraints__ = [
        TableConstraint(
            None,
            TableConstraintType.UNIQUE,
            name="uq_code_status",
            columns=["code", "status"],
        ),
    ]

    id: int
    code: str
    status: str


class WithTableIndexesOverride(ActiveRecord):
    __table_name__ = "with_table_indexes_override"
    __table_indexes__ = [
        IndexDefinition(None, name="idx_table_level", columns=["id"]),
    ]

    id: int
    email: Annotated[str, UseIndex("idx_field_level")]


class WithNullable(ActiveRecord):
    __table_name__ = "with_nullable"

    id: int
    nickname: Optional[str] = None
    note: Annotated[Optional[str], UseConstraint(ColumnConstraintType.NULL)] = None
    required: str = "x"


class WithIdentity(ActiveRecord):
    __table_name__ = "with_identity"

    id: Annotated[
        int,
        UseColumnAttributes(IdentityAttribute(generation="BY DEFAULT")),
    ]


class ForeignAttribute(ColumnAttribute):
    """A stand-in for a backend-owned column attribute."""

    kind = "foreign_custom"
    owner_backend = "mysql"


class WithForeignAttribute(ActiveRecord):
    __table_name__ = "with_foreign_attribute"

    id: int
    name: Annotated[str, UseColumnAttributes(ForeignAttribute())]


class UnknownAttribute(ColumnAttribute):
    """A generic-owned attribute kind no dialect renders."""

    kind = "unknown_kind"


class WithUnknownAttribute(ActiveRecord):
    __table_name__ = "with_unknown_attribute"

    id: int
    name: Annotated[str, UseColumnAttributes(UnknownAttribute())]


class ForeignPartitionClause(PartitionClause):
    """A stand-in for a backend-owned partition clause."""

    owner_backend = "postgres"


class WithForeignPartition(ActiveRecord):
    __table_name__ = "with_foreign_partition"

    id: int

    @classmethod
    def table_partition(cls):
        return ForeignPartitionClause(
            None, PartitionStrategy.HASH, keys=[Column(None, "id")]
        )


class BadColumnName(ActiveRecord):
    __table_name__ = "bad_column_name"

    id: int

    @classmethod
    def column_name(cls, field):
        return 123


class OverrideStatementCandidates(ActiveRecord):
    __table_name__ = "override_statement_candidates"
    __create_table_statement__ = None

    id: int

    @classmethod
    def create_table_statement_classes(cls):
        return cls.__create_table_statement__


class CustomCreateTableExpression(CreateTableExpression):
    """A stand-in for a backend-specific CREATE TABLE statement."""

    owner_backend = "mysql"


class NoFormatCreateTableExpression(CreateTableExpression):
    """A statement class whose rendering method is not provided."""

    @property
    def format_method(self) -> str:
        return "format_no_such_statement"


@pytest.fixture
def backend():
    instance = SQLiteBackend(SQLiteConnectionConfig(database=":memory:"))
    for model in (
        WithAttributes, CompositeWithIndex, WithTableConstraints,
        WithTableIndexesOverride, WithNullable, WithIdentity,
        WithForeignAttribute, WithUnknownAttribute, WithForeignPartition,
        BadColumnName, OverrideStatementCandidates,
    ):
        model.__backend__ = instance
    return instance


# ---------------------------------------------------------------------------
# §5.1 marker candidate types are restricted
# ---------------------------------------------------------------------------


def test_use_sql_type_rejects_datatype_base():
    from rhosocial.activerecord.backend.expression.types import DataType

    with pytest.raises(TypeError):
        UseSqlType(DataType())


def test_use_column_attributes_rejects_non_attribute():
    with pytest.raises(TypeError):
        UseColumnAttributes("NOCASE")


def test_use_column_attributes_rejects_empty():
    with pytest.raises(TypeError):
        UseColumnAttributes()


def test_use_column_attributes_deduplicates():
    marker = UseColumnAttributes(CollationAttribute(name="NOCASE"), CollationAttribute(name="NOCASE"))
    assert len(marker.attributes) == 1


def test_use_constraint_rejects_primary_key():
    with pytest.raises(ValueError, match="__primary_key__"):
        UseConstraint(ColumnConstraintType.PRIMARY_KEY)


def test_column_constraint_type_dropped_identity_and_collate():
    """§5.3: IDENTITY/COLLATE migrated to the column-attribute channel, so the
    constraint type enum no longer carries them."""
    assert not hasattr(ColumnConstraintType, "IDENTITY")
    assert not hasattr(ColumnConstraintType, "COLLATE")


# ---------------------------------------------------------------------------
# §5.2 primary key: single source, single-column lands on the column
# ---------------------------------------------------------------------------


def test_composite_pk_member_gets_not_null_and_table_pk(backend):
    sql, _ = CompositeWithIndex.ddl().create_table().to_sql()
    # §5.7: every composite PK member is forced NOT NULL.
    assert '"order_id" INTEGER NOT NULL' in sql
    assert '"product_id" INTEGER NOT NULL' in sql
    assert 'PRIMARY KEY ("order_id", "product_id")' in sql


def test_composite_pk_becomes_table_constraint_via_interface(backend):
    constraints = CompositeWithIndex.table_constraints()
    assert [c.constraint_type for c in constraints] == [TableConstraintType.PRIMARY_KEY]


# ---------------------------------------------------------------------------
# §5.3 identity / collation ride the column-attribute channel
# ---------------------------------------------------------------------------


def test_identity_attribute_is_collected_and_rendered(backend):
    assert len(WithIdentity.column_attributes("id")) == 1
    sql, _ = WithIdentity.ddl().create_table().to_sql()
    assert "GENERATED BY DEFAULT AS IDENTITY" in sql


def test_identity_attribute_forces_not_null(backend):
    sql, _ = WithIdentity.ddl().create_table().to_sql()
    # §5.7: identity forces NOT NULL (rendered after the identity clause).
    assert "GENERATED BY DEFAULT AS IDENTITY" in sql
    assert '"id" INTEGER GENERATED BY DEFAULT AS IDENTITY' in sql
    assert "NOT NULL" in sql


def test_identity_attribute_parameters_are_rendered(backend):
    sql, _ = WithAttributes.ddl().create_table().to_sql()
    assert "GENERATED ALWAYS AS IDENTITY (START WITH 10 INCREMENT BY 2)" in sql


def test_collation_attribute_is_rendered(backend):
    sql, _ = WithAttributes.ddl().create_table().to_sql()
    assert '"name" TEXT COLLATE NOCASE' in sql


def test_character_set_attribute_is_not_rendered_on_sqlite(backend):
    # character_set is a MySQL/MariaDB kind: the generic dialect skips it.
    sql, _ = WithAttributes.ddl().create_table().to_sql()
    assert "CHARACTER SET" not in sql


def test_foreign_attribute_is_skipped(backend):
    # A foreign-backend attribute is skipped (multi-backend candidates).
    assert WithForeignAttribute.column_attributes("name")
    assert WithForeignAttribute.ddl().create_table().columns[1].attributes == []


def test_unknown_generic_attribute_raises(backend):
    # A generic-owned attribute this dialect cannot render raises (§5.6).
    with pytest.raises(Exception, match="column_attributes"):
        WithUnknownAttribute.ddl().create_table()


# ---------------------------------------------------------------------------
# §5.4 table-level / field-level separation, merged and deduped by name
# ---------------------------------------------------------------------------


def test_field_level_and_table_level_indexes_are_merged_and_deduped(backend):
    # The field's UseIndex name collides with the table-level name: one entry.
    indexes = TableDDLDeriver(CompositeWithIndex, backend.dialect).create_indexes()
    assert [expr.index_name for expr in indexes] == ["idx_pair"]
    assert CompositeWithIndex.table_indexes()[0].name == "idx_pair"


def test_table_indexes_returns_only_table_level(backend):
    assert [i.name for i in WithTableIndexesOverride.table_indexes()] == ["idx_table_level"]
    assert [i.name for i in WithTableIndexesOverride.column_indexes("email")] == ["idx_field_level"]


def test_overriding_table_indexes_leaves_field_level_intact(backend):
    # §5.4: the override only affects the table level.
    indexes = TableDDLDeriver(WithTableIndexesOverride, backend.dialect).create_indexes()
    assert sorted(expr.index_name for expr in indexes) == ["idx_field_level", "idx_table_level"]


def test_table_constraints_constant_is_read(backend):
    constraints = WithTableConstraints.table_constraints()
    assert [c.name for c in constraints] == ["uq_code_status"]
    sql, _ = WithTableConstraints.ddl().create_table().to_sql()
    assert 'CONSTRAINT "uq_code_status" UNIQUE ("code", "status")' in sql


# ---------------------------------------------------------------------------
# §5.6 candidate selection is never silent
# ---------------------------------------------------------------------------


def test_single_value_all_inapplicable_raises(backend):
    # A non-empty single-value declaration with no applicable candidate
    # raises — silent None / dropping is forbidden.
    with pytest.raises(Exception, match="table_partition"):
        WithForeignPartition.ddl().create_table()


def test_additive_foreign_candidates_are_skipped(backend):
    class ForeignIndexDefinition(IndexDefinition):
        owner_backend = "mysql"

    class MixedIndexes(ActiveRecord):
        __table_name__ = "mixed_indexes"
        __table_indexes__ = [
            ForeignIndexDefinition(None, name="idx_foreign", columns=["id"]),
            IndexDefinition(None, name="idx_generic", columns=["id"]),
        ]

        id: int

    MixedIndexes.__backend__ = backend
    names = [expr.index_name for expr in TableDDLDeriver(MixedIndexes, backend.dialect).create_indexes()]
    assert names == ["idx_generic"]


def test_additive_owned_but_unsupported_raises(backend):
    class HashOnlyIndex(ActiveRecord):
        __table_name__ = "hash_only_index"
        __table_indexes__ = [
            IndexDefinition(None, name="idx_hash", columns=["id"], type="HASH"),
        ]

        id: int

    HashOnlyIndex.__backend__ = backend
    # SQLite cannot render a HASH index: the owned/generic candidate raises.
    with pytest.raises(Exception, match="table_indexes"):
        TableDDLDeriver(HashOnlyIndex, backend.dialect).create_indexes()


# ---------------------------------------------------------------------------
# §5.9 batch access: columns_*(fields=None) -> Dict
# ---------------------------------------------------------------------------


def test_batch_interfaces_visit_all_fields(backend):
    names = WithAttributes.columns_name()
    assert names == {"id": "id", "name": "name", "seq": "seq", "charset": "charset"}
    types = WithAttributes.columns_type()
    assert set(types) == set(WithAttributes.model_fields)


def test_batch_interfaces_visit_selected_fields(backend):
    constraints = WithNullable.columns_constraints(["required", "nickname"])
    assert set(constraints) == {"required", "nickname"}
    # §5.7: required → NOT NULL, Optional → no clause.
    assert [c.constraint_type for c in constraints["required"]] == [ColumnConstraintType.NOT_NULL]
    assert constraints["nickname"] == []


def test_batch_indexes_and_attributes(backend):
    indexes = WithTableIndexesOverride.columns_indexes()
    assert [i.name for i in indexes["email"]] == ["idx_field_level"]
    attributes = WithAttributes.columns_attributes()
    assert [type(a).__name__ for a in attributes["name"]] == ["CollationAttribute"]


def test_batch_generated_and_options_default_empty(backend):
    assert WithNullable.columns_generated() == {"id": None, "nickname": None, "note": None, "required": None}
    assert WithNullable.columns_options() == {"id": None, "nickname": None, "note": None, "required": None}


# ---------------------------------------------------------------------------
# §5.7 nullability details
# ---------------------------------------------------------------------------


def test_explicit_null_is_kept_for_non_pk(backend):
    sql, _ = WithNullable.ddl().create_table().to_sql()
    assert '"note" TEXT NULL' in sql


def test_explicit_null_on_pk_member_is_discarded(backend):
    class NullablePk(ActiveRecord):
        __table_name__ = "nullable_pk"
        id: Annotated[Optional[int], UseConstraint(ColumnConstraintType.NULL)] = None

    NullablePk.__backend__ = backend
    sql, _ = NullablePk.ddl().create_table().to_sql()
    # A PRIMARY KEY column is NOT NULL by definition: the contradictory
    # explicit NULL is discarded.
    assert '"id" INTEGER PRIMARY KEY' in sql
    assert '"id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL' in sql


def test_required_with_default_zero_adds_not_null(backend):
    sql, _ = WithNullable.ddl().create_table().to_sql()
    assert '"required" TEXT NOT NULL' in sql


# ---------------------------------------------------------------------------
# §5.12 statement-family candidates
# ---------------------------------------------------------------------------


def test_statement_candidates_default_to_generic(backend):
    expression = WithNullable.ddl().create_table()
    assert type(expression) is CreateTableExpression


def test_statement_candidates_model_override_selects_most_fitting(backend):
    # A foreign class first, generic last: the generic form is selected here.
    OverrideStatementCandidates.__create_table_statement__ = [
        CustomCreateTableExpression, CreateTableExpression,
    ]
    try:
        expression = OverrideStatementCandidates.ddl().create_table()
        assert type(expression) is CreateTableExpression
    finally:
        OverrideStatementCandidates.__create_table_statement__ = None


def test_statement_candidates_model_override_all_inapplicable_raises(backend):
    OverrideStatementCandidates.__create_table_statement__ = [CustomCreateTableExpression]
    try:
        with pytest.raises(Exception, match="create_table"):
            OverrideStatementCandidates.ddl().create_table()
    finally:
        OverrideStatementCandidates.__create_table_statement__ = None


def test_statement_candidates_dialect_preferred_class_is_used():
    class PreferredDialect(SQLiteDialect):
        def preferred_create_table_statement(self):
            return CustomCreateTableExpression

    class PreferredModel(ActiveRecord):
        __table_name__ = "preferred_model"
        id: int

    PreferredModel.__backend__ = SQLiteBackend(SQLiteConnectionConfig(database=":memory:"))
    # The preferred class is owned by "mysql" (foreign here): the generic
    # form is selected instead — foreign candidates never win on this dialect.
    expression = PreferredModel.ddl().create_table()
    assert type(expression) is CreateTableExpression


# ---------------------------------------------------------------------------
# §5.13/§5.14 statement parameter contract (Gate 0)
# ---------------------------------------------------------------------------


def test_param_schema_introspects_canonical_parameters():
    schema = StatementParamSchema(CreateTableExpression)
    params = schema.parameters(CreateTableExpression)
    assert "table" in params
    assert "columns" in params
    assert "indexes" in params
    assert "table_constraints" in params
    assert "storage_options" in params
    assert "partition" in params
    assert "table_options" in params
    assert "temporary" in params
    assert "if_not_exists" in params
    assert "self" not in params
    assert "dialect" not in params


def test_param_schema_detects_missing_parameters():
    schema = StatementParamSchema(CreateTableExpression)

    class NarrowCreateTableExpression(CreateTableExpression):
        def __init__(self, dialect, table, columns):
            super().__init__(dialect, table, columns)

    collected = {"table": "t", "columns": [], "indexes": []}
    missing = schema.missing_params(NarrowCreateTableExpression, collected)
    assert "indexes" in missing
    assert "table" not in missing


def test_param_schema_accepts_kwargs_passthrough():
    schema = StatementParamSchema(CreateTableExpression)

    class KwargsCreateTableExpression(CreateTableExpression):
        def __init__(self, dialect, *args, **kwargs):
            super().__init__(dialect, *args, **kwargs)

    assert schema.missing_params(KwargsCreateTableExpression, {"bogus": 1}) == []


def test_param_schema_instantiates_keyword_only(backend):
    schema = StatementParamSchema(CreateTableExpression)
    expression = schema.instantiate(
        CreateTableExpression,
        backend.dialect,
        {
            "table": "t",
            "columns": [],
            "temporary": True,
            "if_not_exists": True,
        },
    )
    assert isinstance(expression, CreateTableExpression)
    assert expression.temporary is True
    assert expression.if_not_exists is True


def test_param_schema_rejects_incompatible_class(backend):
    schema = StatementParamSchema(CreateTableExpression)

    class NarrowCreateTableExpression(CreateTableExpression):
        def __init__(self, dialect, table, columns):
            super().__init__(dialect, table, columns)

    with pytest.raises(StatementContractError, match="indexes"):
        schema.instantiate(
            NarrowCreateTableExpression,
            backend.dialect,
            {"table": "t", "columns": [], "indexes": []},
        )


def test_active_ddl_returns_table_expression(backend):
    expression = WithNullable.ddl().create_table()
    assert isinstance(expression, CreateTableExpression)
    assert expression.to_sql()[0].startswith("CREATE TABLE")


def test_no_format_statement_class_is_not_renderable():
    # Gate 2 for statements: the dialect provides the declared format method.
    from rhosocial.activerecord.ddl import TableDDLDeriver

    deriver = TableDDLDeriver.__new__(TableDDLDeriver)
    deriver.dialect = SQLiteDialect((3, 53, 0))
    assert deriver._statement_renderable(NoFormatCreateTableExpression) is False
    assert deriver._statement_renderable(CreateTableExpression) is True


def test_column_name_contract_rejects_non_str(backend):
    with pytest.raises(TypeError):
        BadColumnName.ddl().create_table()


# ---------------------------------------------------------------------------
# Unsupported-feature error still surfaces at render time (§6-D B5)
# ---------------------------------------------------------------------------


def test_inline_indexes_override_true_raises_on_sqlite(backend):
    expression = WithTableIndexesOverride.ddl().create_table(inline_indexes=True)
    assert sorted(index.name for index in expression.indexes) == [
        "idx_field_level", "idx_table_level",
    ]
    with pytest.raises(UnsupportedFeatureError):
        expression.to_sql()


def test_identity_attribute_parameters_survive_expression_generation(backend):
    first = WithIdentity.ddl().create_table()
    second = WithIdentity.ddl().create_table()
    assert first.to_sql() == second.to_sql()
