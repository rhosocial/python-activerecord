# tests/rhosocial/activerecord_test/feature/basic/ddl/test_ddl_declaration_interfaces.py
"""Tests for the dialect-free ActiveRecord DDLSource declaration contract."""

from typing import Optional

try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

import pytest

from rhosocial.activerecord.backend.expression import QueryExpression
from rhosocial.activerecord.backend.expression.core import Column
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression.statements.ddl_partition import (
    PartitionClause,
    PartitionStrategy,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnConstraintType,
    IndexDefinition,
    TableConstraint,
    TableConstraintType,
)
from rhosocial.activerecord.backend.expression.statements.ddl_view import (
    ViewCheckOption,
    ViewOptions,
)
from rhosocial.activerecord.backend.expression.types import DataType
from rhosocial.activerecord.base import (
    CharacterSetAttribute,
    DDLSourceMixin,
    CollationAttribute,
    ColumnAttribute,
    ColumnOptions,
    DDLAnnotation,
    DDLFieldMetadata,
    DDLSource,
    IdentityAttribute,
    ObjectDeclaration,
    UseColumnAttributes,
    UseComment,
    UseConstraint,
    UseGeneratedColumn,
    UseIndex,
    UseSqlType,
)
from rhosocial.activerecord.model import ActiveRecord


class Plain(ActiveRecord):
    __table_name__ = "plain"

    id: int
    name: str


class Composite(ActiveRecord):
    __table_name__ = "composite"
    __primary_key__ = ("order_id", "product_id")
    __table_indexes__ = [
        IndexDefinition(None, name="idx_pair", columns=["order_id", "product_id"]),
    ]

    order_id: int
    product_id: int
    quantity: int


class CompositeWithDeclaredPrimaryKey(ActiveRecord):
    __table_name__ = "composite_with_declared_primary_key"
    __primary_key__ = ("order_id", "product_id")
    __table_constraints__ = [
        TableConstraint(
            None,
            TableConstraintType.PRIMARY_KEY,
            columns=["order_id", "product_id"],
        ),
    ]

    order_id: int
    product_id: int


class WithTableConstraint(ActiveRecord):
    __table_name__ = "with_table_constraint"
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


class WithFieldIndex(ActiveRecord):
    __table_name__ = "with_field_index"
    __table_indexes__ = [
        IndexDefinition(None, name="idx_table_email", columns=["email"]),
    ]

    id: int
    email: Annotated[str, UseIndex("idx_field_email")]


class WithAttributes(ActiveRecord):
    __table_name__ = "with_attributes"

    id: int
    name: Annotated[str, UseColumnAttributes(CollationAttribute(name="NOCASE"))]
    seq: Annotated[
        int,
        UseColumnAttributes(IdentityAttribute(generation="ALWAYS", start=10, increment=2)),
    ]
    charset: Annotated[str, UseColumnAttributes(CharacterSetAttribute(name="utf8mb4"))]


class WithNullable(ActiveRecord):
    __table_name__ = "with_nullable"

    id: int
    nickname: Annotated[Optional[str], UseConstraint(ColumnConstraintType.NULL)] = None
    note: Annotated[Optional[str], UseConstraint(ColumnConstraintType.NOT_NULL)] = None
    required: str = "x"


class WithDerivedDeclarations(ActiveRecord):
    __table_name__ = "with_derived_declarations"

    id: int
    label: Annotated[str, UseComment("display label")]
    computed: Annotated[str, UseGeneratedColumn(lambda dialect: object())]


class ForeignAttribute(ColumnAttribute):
    kind = "foreign_custom"


class WithForeignAttribute(ActiveRecord):
    __table_name__ = "with_foreign_attribute"

    id: int
    name: Annotated[str, UseColumnAttributes(ForeignAttribute())]


class ForeignPartitionClause(PartitionClause):
    owner_backend = "postgres"


class WithForeignPartition(ActiveRecord):
    __table_name__ = "with_foreign_partition"

    id: int

    @classmethod
    def table_partition(cls):
        return ForeignPartitionClause(
            None,
            PartitionStrategy.HASH,
            keys=[Column(None, "id")],
        )


class UnhandledAnnotation(DDLAnnotation):
    pass


class WithUnhandledAnnotation(ActiveRecord):
    __table_name__ = "with_unhandled_annotation"

    id: int
    value: Annotated[str, UnhandledAnnotation()]


def test_activerecord_satisfies_ddl_source():
    assert isinstance(Plain, DDLSource)


def test_marker_type_contracts():
    with pytest.raises(TypeError):
        UseSqlType(DataType())
    with pytest.raises(TypeError):
        UseColumnAttributes("NOCASE")
    with pytest.raises(TypeError):
        UseColumnAttributes()
    with pytest.raises(ValueError):
        UseConstraint(ColumnConstraintType.PRIMARY_KEY)
    with pytest.raises(ValueError):
        IdentityAttribute(generation="SOMETIMES")
    with pytest.raises(ValueError):
        CollationAttribute(name="")
    with pytest.raises(ValueError):
        CharacterSetAttribute(name="")


def test_column_options_base_contract():
    options = ColumnOptions()
    assert options.column_definition_class().__name__ == "ColumnDefinition"
    assert options.apply_to(object()) is None
    metadata = DDLFieldMetadata(Plain.model_fields["id"])
    with pytest.raises(TypeError, match="ColumnOptions"):
        metadata.add_column_options(object())


def test_single_primary_key_is_added_to_column_declaration():
    constraint_types = {
        constraint.constraint_type
        for constraint in Plain.column_constraints("id")
    }
    assert ColumnConstraintType.PRIMARY_KEY in constraint_types
    assert ColumnConstraintType.NOT_NULL in constraint_types


def test_composite_primary_key_is_added_as_table_constraint():
    order_id_types = {
        constraint.constraint_type
        for constraint in Composite.column_constraints("order_id")
    }
    assert ColumnConstraintType.PRIMARY_KEY not in order_id_types
    assert ColumnConstraintType.NOT_NULL in order_id_types

    primary_keys = [
        constraint
        for constraint in Composite.table_constraints()
        if constraint.constraint_type == TableConstraintType.PRIMARY_KEY
    ]
    assert len(primary_keys) == 1
    assert primary_keys[0].columns == ["order_id", "product_id"]


def test_declared_composite_primary_key_is_not_duplicated():
    primary_keys = [
        constraint
        for constraint in CompositeWithDeclaredPrimaryKey.table_constraints()
        if constraint.constraint_type == TableConstraintType.PRIMARY_KEY
    ]
    assert len(primary_keys) == 1
    assert primary_keys[0].columns == ["order_id", "product_id"]


def test_table_constraints_are_returned_unchanged():
    constraints = WithTableConstraint.table_constraints()
    assert len(constraints) == 1
    assert constraints[0].name == "uq_code_status"
    assert constraints[0].columns == ["code", "status"]


def test_field_and_table_indexes_remain_separate_declarations():
    field_indexes = WithFieldIndex.column_indexes("email")
    table_indexes = WithFieldIndex.table_indexes()
    assert [index.name for index in field_indexes] == ["idx_field_email"]
    assert [index.name for index in table_indexes] == ["idx_table_email"]
    assert field_indexes[0].columns == ["email"]


def test_column_attributes_are_returned_without_dialect_selection():
    assert isinstance(WithAttributes.column_attributes("name")[0], CollationAttribute)
    identity = WithAttributes.column_attributes("seq")[0]
    assert isinstance(identity, IdentityAttribute)
    assert identity.generation == "ALWAYS"
    assert identity.start == 10
    assert identity.increment == 2
    assert isinstance(WithAttributes.column_attributes("charset")[0], CharacterSetAttribute)
    assert isinstance(WithForeignAttribute.column_attributes("name")[0], ForeignAttribute)


def test_nullable_declarations_follow_primary_key_rules():
    nickname_types = {
        constraint.constraint_type
        for constraint in WithNullable.column_constraints("nickname")
    }
    note_types = {
        constraint.constraint_type
        for constraint in WithNullable.column_constraints("note")
    }
    required_types = {
        constraint.constraint_type
        for constraint in WithNullable.column_constraints("required")
    }
    assert nickname_types == {ColumnConstraintType.NULL}
    assert note_types == {ColumnConstraintType.NOT_NULL}
    assert required_types == {ColumnConstraintType.NOT_NULL}


def test_comment_and_generated_declarations_are_exposed():
    assert WithDerivedDeclarations.column_comment("label") == "display label"
    generated = WithDerivedDeclarations.generated_column("computed")
    assert callable(generated)


def test_batch_interfaces_cover_all_or_selected_fields():
    assert tuple(WithAttributes.columns_name().values()) == ("id", "name", "seq", "charset")
    assert WithAttributes.columns_name(["name"]) == {"name": "name"}
    assert set(WithAttributes.columns_constraints()) == {"id", "name", "seq", "charset"}
    assert set(WithAttributes.columns_indexes()) == {"id", "name", "seq", "charset"}


def test_table_partition_declaration_is_returned_unchanged():
    declaration = WithForeignPartition.table_partition()
    assert isinstance(declaration, ForeignPartitionClause)
    assert declaration.method == PartitionStrategy.HASH.value
    assert declaration.keys[0].name == "id"


def test_default_table_interfaces_are_empty_or_none():
    assert Plain.table_options() is None
    assert Plain.table_storage_options() is None
    assert Plain.table_partition() is None
    assert Plain.table_inherits() is None
    assert Plain.table_tablespace() is None
    assert Plain.create_table_statement_classes() is None


# ---------------------------------------------------------------------------
# Object kind: table vs. view vs. materialized view
#
# object_type() is a declaration, never a probe. Nothing here asks the database
# what the object actually is; the DDL layer reads the value to choose a
# statement and then applies the dialect's capability gates.
# ---------------------------------------------------------------------------


class MaterializedSummary(ActiveRecord):
    __table_name__ = "order_summary"
    id: Optional[int] = None

    @classmethod
    def object_type(cls):
        return ObjectDeclaration.MATERIALIZED_VIEW

    @classmethod
    def view_dependencies(cls):
        return ("orders",)

    @classmethod
    def view_options(cls):
        return ViewOptions(check_option=ViewCheckOption.LOCAL)


class ViewDDLSource(DDLSourceMixin):
    """A view declared with no model behind it.

    Satisfying DDLSource needs the four identity methods a model would
    normally supply -- table_name, schema_name, primary_key_columns and
    is_composite_pk -- on top of everything DDLSourceMixin provides. That is
    the whole cost of a non-model declaration source, and it is the reason a
    plain view is expressible here at all.
    """

    @classmethod
    def table_name(cls):
        return "revenue_by_customer"

    @classmethod
    def schema_name(cls):
        return None

    @classmethod
    def primary_key_columns(cls):
        return ()

    @classmethod
    def is_composite_pk(cls):
        return False

    @classmethod
    def object_type(cls):
        return ObjectDeclaration.VIEW

    @classmethod
    def view_options(cls):
        return ViewOptions(check_option=ViewCheckOption.LOCAL)

    @classmethod
    def view_definition(cls):
        return lambda dialect: QueryExpression(
            dialect,
            select=[Column(dialect, "name")],
            **{},
        )

    @classmethod
    def view_dependencies(cls):
        return ("orders", "customers")


def test_object_type_defaults_to_table():
    assert Plain.object_type() == ObjectDeclaration.TABLE


def test_default_view_declarations_are_none():
    assert Plain.view_options() is None
    assert Plain.view_definition() is None
    assert Plain.view_dependencies() is None


def test_a_model_can_declare_a_materialized_view():
    assert MaterializedSummary.object_type() == ObjectDeclaration.MATERIALIZED_VIEW
    assert MaterializedSummary.view_dependencies() == ("orders",)
    assert MaterializedSummary.view_options().check_option == ViewCheckOption.LOCAL


def test_a_model_can_declare_a_plain_view():
    """The value is a declaration; nothing verifies it against the database."""

    class PlainView(MaterializedSummary):
        __table_name__ = "revenue_by_customer"

        @classmethod
        def object_type(cls):
            return ObjectDeclaration.VIEW

    assert PlainView.object_type() == ObjectDeclaration.VIEW


def test_object_type_is_not_a_probe():
    """Declaring MATERIALIZED_VIEW does not require a connection or a table."""
    assert MaterializedSummary.backend is not None
    assert MaterializedSummary.object_type() == ObjectDeclaration.MATERIALIZED_VIEW


def test_a_non_model_ddl_source_can_declare_a_view():
    assert isinstance(ViewDDLSource, DDLSource)
    assert ViewDDLSource.object_type() == ObjectDeclaration.VIEW
    assert ViewDDLSource.view_dependencies() == ("orders", "customers")
    assert ViewDDLSource.view_options().check_option == ViewCheckOption.LOCAL


def test_view_definition_is_a_dialect_bound_factory():
    """Not called at class-definition time -- a dialect does not exist yet."""
    factory = ViewDDLSource.view_definition()
    assert callable(factory)
    expression = factory(DummyDialect())
    assert expression.to_sql()[0].startswith("SELECT")


def test_the_four_identity_methods_are_the_whole_cost_of_no_model():
    """What DDLSourceMixin alone does not provide, spelled out.

    Worth pinning: it is the reason a non-model declaration source is a
    handful of methods rather than a subclassing exercise.
    """
    members = [
        name
        for name in dir(DDLSource)
        if not name.startswith("_") and callable(getattr(DDLSource, name, None))
    ]
    missing = sorted(name for name in members if not hasattr(DDLSourceMixin, name))
    assert missing == ["is_composite_pk", "primary_key_columns", "schema_name", "table_name"]


def test_object_type_does_not_conflict_with_introspection_table_type():
    """A DDL declaration enum, distinct from the introspection enum.

    ObjectDeclaration is a *declaration* about what the developer intends;
    TableType is an observation of what the database holds. Keeping them apart
    stops a declaration from being mistaken for a reading of the catalog.
    """
    from rhosocial.activerecord.backend.introspection.types import TableType

    assert ObjectDeclaration is not TableType
    assert ObjectDeclaration.MATERIALIZED_VIEW.value == "materialized_view"
    assert not hasattr(TableType, "MATERIALIZED_VIEW")


def test_unhandled_annotation_requires_explicit_handler():
    with pytest.raises(TypeError, match="explicit handler"):
        WithUnhandledAnnotation.ddl_field_names()
