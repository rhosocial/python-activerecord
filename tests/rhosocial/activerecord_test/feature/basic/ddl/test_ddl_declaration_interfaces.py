# tests/rhosocial/activerecord_test/feature/basic/ddl/test_ddl_declaration_interfaces.py
"""Tests for the dialect-free ActiveRecord DDLSource declaration contract."""
from rhosocial.activerecord.backend.expression.statements import (
    ColumnNotNullConstraint,
    ColumnNullableConstraint,
    ColumnPrimaryKeyConstraint,
    TablePrimaryKeyConstraint,
    TableUniqueConstraint,
)
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import DefaultTimestampMixin
from rhosocial.activerecord.base import (
    CharacterSetAttribute,
    CollationAttribute,
    ColumnAttribute,
    ColumnOptions,
    DDLAnnotation,
    DDLFieldMetadata,
    DDLSource,
    IdentityAttribute,
    ObjectDeclaration,
    UseColumn,
    UseColumnAttributes,
    UseComment,
    UseConstraint,
    UseGeneratedColumn,
    UseIndex,
    UsePartitionKey,
    UseSqlType,
)
from rhosocial.activerecord.backend.expression.types import DataType, TextType
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    IndexDefinition,
    TableConstraint,
)
from rhosocial.activerecord.backend.expression.statements.ddl_partition import (
    PartitionClause,
    PartitionStrategy,
)
from rhosocial.activerecord.backend.expression.core import Column
from typing import Optional

import pytest

try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated



class Plain(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "plain"

    id: int
    name: str


class Composite(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "composite"

    @classmethod
    def primary_key(cls):
        return ("order_id", "product_id")

    __table_indexes__ = [
        IndexDefinition(None, name="idx_pair", columns=["order_id", "product_id"]),
    ]

    order_id: int
    product_id: int
    quantity: int


class CompositeWithDeclaredPrimaryKey(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "composite_with_declared_primary_key"

    @classmethod
    def primary_key(cls):
        return ("order_id", "product_id")

    __table_constraints__ = [
        TableConstraint(None, branch=TablePrimaryKeyConstraint(None, ["order_id", "product_id"])),
    ]

    order_id: int
    product_id: int


class WithTableConstraint(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "with_table_constraint"

    __table_constraints__ = [
        TableConstraint(None, branch=TableUniqueConstraint(None, ["code", "status"]), name="uq_code_status"),
    ]

    id: int
    code: str
    status: str


class WithFieldIndex(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "with_field_index"

    __table_indexes__ = [
        IndexDefinition(None, name="idx_table_email", columns=["email"]),
    ]

    id: int
    email: Annotated[str, UseIndex("idx_field_email")]


class WithAttributes(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "with_attributes"

    id: int
    name: Annotated[str, UseColumnAttributes(CollationAttribute(name="NOCASE"))]
    seq: Annotated[
        int,
        UseColumnAttributes(IdentityAttribute(generation="ALWAYS", start=10, increment=2)),
    ]
    charset: Annotated[str, UseColumnAttributes(CharacterSetAttribute(name="utf8mb4"))]


class WithNullable(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "with_nullable"

    id: int
    nickname: Annotated[Optional[str], UseConstraint(ColumnNullableConstraint)] = None
    note: Annotated[Optional[str], UseConstraint(ColumnNotNullConstraint)] = None
    required: str = "x"


class WithDerivedDeclarations(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "with_derived_declarations"

    id: int
    label: Annotated[str, UseComment("display label")]
    computed: Annotated[str, UseGeneratedColumn(lambda dialect: object())]


#: The marker classes, the field of ``EveryRegisteredMarker`` that carries each
#: one, and the attribute the registry says it lands on. Written out here so the
#: registry is checked against an expectation rather than against itself.
_MARKER_FIELDS = {
    UseSqlType: "sql_typed",
    UseConstraint: "constrained",
    UseIndex: "indexed",
    UseColumnAttributes: "attributed",
    UseComment: "commented",
    UseGeneratedColumn: "generated",
    UsePartitionKey: "partition_keyed",
}


class ForeignAttribute(ColumnAttribute):
    kind = "foreign_custom"

class WithForeignAttribute(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "with_foreign_attribute"

    id: int
    name: Annotated[str, UseColumnAttributes(ForeignAttribute())]


class ForeignPartitionClause(PartitionClause):
    owner_backend = "postgres"


class WithForeignPartition(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "with_foreign_partition"

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
    @classmethod
    def table_name(cls):
        return "with_unhandled_annotation"

    id: int
    value: Annotated[str, UnhandledAnnotation()]


class EveryRegisteredMarker(ActiveRecord):
    """One field per core marker, so the registry can be walked against them."""

    @classmethod
    def table_name(cls):
        return "every_registered_marker"

    id: int
    sql_typed: Annotated[str, UseSqlType(TextType())]
    constrained: Annotated[Optional[str], UseConstraint(ColumnNullableConstraint)] = None
    indexed: Annotated[str, UseIndex("idx_every_registered_marker")]
    attributed: Annotated[str, UseColumnAttributes(CollationAttribute(name="NOCASE"))]
    commented: Annotated[str, UseComment("a comment")]
    generated: Annotated[str, UseGeneratedColumn(lambda dialect: object())]
    partition_keyed: Annotated[str, UsePartitionKey()]


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
        UseConstraint(ColumnPrimaryKeyConstraint)
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


def test_the_marker_registry_is_what_the_declaration_interface_reads():
    """Which marker writes which attribute, and in what plurality.

    ``MARKER_REGISTRY`` is read once -- by ``DDLFieldMetadata.__init__`` -- and
    the attribute name it holds is what the DDL layer then reads. A rename in the
    registry therefore stops being what the layer reads, and a rename in the
    layer stops being what the registry writes, with nothing saying so. The
    expected mapping is written out here, and the marker classes are the same
    six the annotation handler dispatches, which is the other list that has to
    agree with it and nothing keeps in step with it either.
    """
    from rhosocial.activerecord.base.ddl import (
        DDLAnnotationHandler,
        MARKER_REGISTRY,
    )

    expected = {
        UseSqlType: ("use_sql_type", True),
        UseConstraint: ("constraints", False),
        UseIndex: ("indexes", False),
        UseColumnAttributes: ("column_attributes", False),
        UseComment: ("column_comment", True),
        UseGeneratedColumn: ("generated_column", True),
        UsePartitionKey: ("partition_key", True),
    }
    assert MARKER_REGISTRY == expected, (
        f"the registry writes {sorted(attr for attr, _ in MARKER_REGISTRY.values())} "
        f"and the declaration interface reads "
        f"{sorted(attr for attr, _ in expected.values())}"
    )
    assert set(MARKER_REGISTRY) == set(DDLAnnotationHandler.annotation_types), (
        f"collected but never dispatched: "
        f"{sorted(c.__name__ for c in set(MARKER_REGISTRY) - set(DDLAnnotationHandler.annotation_types))}; "
        f"dispatched but never collected: "
        f"{sorted(c.__name__ for c in set(DDLAnnotationHandler.annotation_types) - set(MARKER_REGISTRY))}"
    )


def test_a_marker_reaches_its_attribute_in_the_plurality_its_entry_promises():
    """``singular`` is the difference between one marker and a tuple of them.

    The flag decides the shape of every attribute the DDL layer reads, and a
    flipped one is invisible in the registry: it shows up as a tuple where the
    code takes a marker, or as one marker where the code takes all of them.
    """
    from rhosocial.activerecord.base.ddl import MARKER_REGISTRY

    fields = EveryRegisteredMarker.model_fields
    for marker_class, (attr_name, singular) in MARKER_REGISTRY.items():
        metadata = DDLFieldMetadata(fields[_MARKER_FIELDS[marker_class]])
        value = getattr(metadata, attr_name)
        if singular:
            assert isinstance(value, marker_class), (
                f"{marker_class.__name__} is registered singular, so "
                f"{attr_name} must hold the marker itself, got {value!r}"
            )
        else:
            assert isinstance(value, tuple), (
                f"{marker_class.__name__} is registered plural, so {attr_name} "
                f"must hold a tuple, got {value!r}"
            )
            assert type(value[0]) is marker_class, (
                f"{attr_name} must hold the {marker_class.__name__} markers, got "
                f"{[type(v).__name__ for v in value]}"
            )


def test_single_primary_key_is_added_to_column_declaration():
    declared = {
        type(constraint.branch)
        for constraint in Plain.column_constraints("id")
    }
    assert ColumnPrimaryKeyConstraint in declared
    assert ColumnNotNullConstraint in declared


def test_composite_primary_key_is_added_as_table_constraint():
    order_id_branches = {
        type(constraint.branch)
        for constraint in Composite.column_constraints("order_id")
    }
    assert ColumnPrimaryKeyConstraint not in order_id_branches
    assert ColumnNotNullConstraint in order_id_branches

    primary_keys = [
        constraint
        for constraint in Composite.table_constraints()
        if isinstance(constraint.branch, TablePrimaryKeyConstraint)
    ]
    assert len(primary_keys) == 1
    assert primary_keys[0].branch.columns == ["order_id", "product_id"]


def test_declared_composite_primary_key_is_not_duplicated():
    primary_keys = [
        constraint
        for constraint in CompositeWithDeclaredPrimaryKey.table_constraints()
        if isinstance(constraint.branch, TablePrimaryKeyConstraint)
    ]
    assert len(primary_keys) == 1
    assert primary_keys[0].branch.columns == ["order_id", "product_id"]


def test_table_constraints_are_returned_unchanged():
    constraints = WithTableConstraint.table_constraints()
    assert len(constraints) == 1
    assert constraints[0].name == "uq_code_status"
    assert constraints[0].branch.columns == ["code", "status"]


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
    nickname_branches = {
        type(constraint.branch)
        for constraint in WithNullable.column_constraints("nickname")
    }
    note_branches = {
        type(constraint.branch)
        for constraint in WithNullable.column_constraints("note")
    }
    required_branches = {
        type(constraint.branch)
        for constraint in WithNullable.column_constraints("required")
    }
    assert nickname_branches == {ColumnNullableConstraint}
    assert note_branches == {ColumnNotNullConstraint}
    assert required_branches == {ColumnNotNullConstraint}


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
    assert Plain.object_type() is ObjectDeclaration.TABLE


class WithMixedAnnotations(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "with_mixed_annotations"

    id: int
    value: Annotated[str, UseColumn("val"), UnhandledAnnotation(), UseComment("mixed")]


class WithTimestamps(DefaultTimestampMixin, ActiveRecord):
    @classmethod
    def table_name(cls):
        return "with_timestamps"

    id: int


def test_table_level_accessors_run_the_unhandled_annotation_gate():
    """The declaration surface no longer rejects annotations it cannot use.

    A marker may belong to a backend this model is never used with; the plan
    generator, not the declaration surface, decides which markers apply.
    """
    assert WithUnhandledAnnotation.table_indexes() == []
    assert WithUnhandledAnnotation.table_constraints() == []
    assert WithUnhandledAnnotation.ddl_field_names() == ("id", "value")


def test_unhandled_annotation_is_still_present_in_the_declaration_surface():
    annotations = WithUnhandledAnnotation.column_annotations("value")
    assert len(annotations) == 1
    assert isinstance(annotations[0], UnhandledAnnotation)


def test_column_annotations_returns_every_marker_unfiltered():
    annotations = WithMixedAnnotations.column_annotations("value")
    assert [type(annotation) for annotation in annotations] == [
        UseColumn,
        UnhandledAnnotation,
        UseComment,
    ]
    assert WithMixedAnnotations.column_name("value") == "val"
    assert WithMixedAnnotations.column_comment("value") == "mixed"


def test_default_timestamp_fields_declare_a_sql_type():
    for field in ("created_at", "updated_at"):
        declared = WithTimestamps.column_data_type(field)
        assert isinstance(declared, UseSqlType)
        assert declared.data_type.name == "timestamp"
