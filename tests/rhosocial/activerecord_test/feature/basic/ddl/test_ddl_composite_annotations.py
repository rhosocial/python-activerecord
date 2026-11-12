# tests/rhosocial/activerecord_test/feature/basic/ddl/test_ddl_composite_annotations.py
"""Composite declarations on the field-level annotation surface.

The anchor rule (D1): an explicit ``columns`` list is authoritative and the
annotated field must be its first (leftmost) column. Violations, unknown
columns and duplicate index names fail at class creation with ``TypeError``.
"""
from rhosocial.activerecord.backend.expression.statements import (
    ColumnForeignKeyConstraint,
    ColumnNotNullConstraint,
    ColumnUniqueConstraint,
    TableForeignKeyConstraint,
    TableUniqueConstraint,
)
from rhosocial.activerecord.backend.expression.objects.relation import Table
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    IndexDefinition,
)
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import UseColumn, UseConstraint, UseIndex

try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

import pytest


class CompositeIndexModel(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "composite_index_model"

    id: int
    email: Annotated[str, UseIndex("idx_email_country", columns=["email", "country"])]
    country: str


class CompositeUniqueModel(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "composite_unique_model"

    id: int
    code: Annotated[
        str,
        UseConstraint(ColumnUniqueConstraint, columns=["code", "status"], name="uq_code_status"),
    ]
    status: str


class CompositeForeignKeyModel(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "composite_foreign_key_model"

    id: int
    order_id: Annotated[
        int,
        UseConstraint(
            ColumnForeignKeyConstraint,
            columns=["order_id", "line_no"],
            references=(Table(None, "orders"), ["order_no", "line_no"]),
            name="fk_order_line",
        ),
    ]
    line_no: int


class TestCompositeUseIndex:
    """A ``columns`` list turns the field-level index into a composite one."""

    def test_composite_definition_is_authoritative(self):
        definitions = CompositeIndexModel.column_indexes("email")
        assert len(definitions) == 1
        definition = definitions[0]
        assert definition.name == "idx_email_country"
        assert definition.columns == ["email", "country"]

    def test_non_anchor_field_has_no_index(self):
        assert CompositeIndexModel.column_indexes("country") == []

    def test_single_column_form_is_unchanged(self):
        # Regression guard: the anchor-only form still yields a one-column
        # definition without declaring ``columns``.
        class WithSingleIndex(ActiveRecord):
            @classmethod
            def table_name(cls):
                return "with_single_index"

            id: int
            email: Annotated[str, UseIndex("idx_email", unique=True)]

        definitions = WithSingleIndex.column_indexes("email")
        assert len(definitions) == 1
        assert definitions[0].columns == ["email"]
        assert definitions[0].unique is True

    def test_columns_shorter_than_two_is_rejected(self):
        with pytest.raises(TypeError):
            class TooShort(ActiveRecord):
                @classmethod
                def table_name(cls):
                    return "too_short"

                id: int
                email: Annotated[str, UseIndex("idx_email", columns=["email"])]

    def test_anchor_not_first_is_rejected_at_class_creation(self):
        with pytest.raises(TypeError, match="leftmost"):
            class AnchorMismatch(ActiveRecord):
                @classmethod
                def table_name(cls):
                    return "anchor_mismatch"

                id: int
                country: Annotated[
                    str,
                    UseIndex("idx_email_country", columns=["email", "country"]),
                ]
                email: str

    def test_unknown_column_is_rejected_at_class_creation(self):
        with pytest.raises(TypeError, match="does not define"):
            class UnknownColumn(ActiveRecord):
                @classmethod
                def table_name(cls):
                    return "unknown_column"

                id: int
                email: Annotated[
                    str,
                    UseIndex("idx_email_country", columns=["email", "nope"]),
                ]
                country: str

    def test_renamed_column_anchor_resolves_through_use_column(self):
        # The anchor is the column, not the field: a renamed anchor matches
        # ``columns[0]`` when the list names the database column.
        class RenamedAnchor(ActiveRecord):
            @classmethod
            def table_name(cls):
                return "renamed_anchor"

            id: int
            email_address: Annotated[
                str,
                UseColumn("email"),
                UseIndex("idx_email_country", columns=["email", "country"]),
            ]
            country: str

        definitions = RenamedAnchor.column_indexes("email_address")
        assert definitions[0].columns == ["email", "country"]

    def test_renamed_anchor_mismatch_is_rejected(self):
        # ``columns`` names database columns: a list naming the Python field
        # name does not match a renamed anchor's column.
        with pytest.raises(TypeError, match="leftmost"):
            class RenamedMismatch(ActiveRecord):
                @classmethod
                def table_name(cls):
                    return "renamed_mismatch"

                id: int
                email_address: Annotated[
                    str,
                    UseColumn("email"),
                    UseIndex("idx_email_country", columns=["email_address", "country"]),
                ]
                country: str


class TestIndexNameConflicts:
    """Index names are unique across both declaration surfaces."""

    def test_field_level_against_table_level_is_rejected(self):
        with pytest.raises(TypeError, match="duplicate index name"):
            class Collision(ActiveRecord):
                @classmethod
                def table_name(cls):
                    return "collision"

                __table_indexes__ = [
                    IndexDefinition(None, name="dup", columns=["email"]),
                ]

                id: int
                email: Annotated[str, UseIndex("dup")]

    def test_field_level_against_field_level_is_rejected(self):
        with pytest.raises(TypeError, match="duplicate index name"):
            class Duplicate(ActiveRecord):
                @classmethod
                def table_name(cls):
                    return "duplicate"

                id: int
                email: Annotated[str, UseIndex("dup")]
                backup_email: Annotated[str, UseIndex("dup")]

    def test_table_level_internal_duplicate_is_rejected(self):
        with pytest.raises(TypeError, match="duplicate index name"):
            class TableDuplicate(ActiveRecord):
                @classmethod
                def table_name(cls):
                    return "table_duplicate"

                __table_indexes__ = [
                    IndexDefinition(None, name="dup", columns=["email"]),
                    IndexDefinition(None, name="dup", columns=["name"]),
                ]

                id: int
                email: str
                name: str

    def test_distinct_names_coexist(self):
        class Coexisting(ActiveRecord):
            @classmethod
            def table_name(cls):
                return "coexisting"

            __table_indexes__ = [
                IndexDefinition(None, name="idx_table_email", columns=["email"]),
            ]

            id: int
            email: Annotated[str, UseIndex("idx_field_email")]

        names = {index.name for index in Coexisting.table_indexes()}
        names.update(
            index.name
            for index in Coexisting.column_indexes("email")
        )
        assert names == {"idx_table_email", "idx_field_email"}


class TestCompositeUseConstraint:
    """A multi-column ``UseConstraint`` surfaces as a table-level fact."""

    def test_multi_column_unique_is_not_column_level(self):
        # Only the implicit NOT NULL rides the column; the composite UNIQUE
        # itself must not appear in the column definition.
        constraints = CompositeUniqueModel.column_constraints("code")
        assert all(
            not isinstance(constraint.branch, ColumnUniqueConstraint)
            for constraint in constraints
        )

    def test_multi_column_unique_surfaces_at_table_level(self):
        constraints = [
            constraint for constraint in CompositeUniqueModel.table_constraints()
            if isinstance(constraint.branch, TableUniqueConstraint)
        ]
        assert len(constraints) == 1
        constraint = constraints[0]
        assert constraint.name == "uq_code_status"
        assert constraint.branch.columns == ["code", "status"]

    def test_multi_column_foreign_key_surfaces_at_table_level(self):
        constraints = [
            constraint for constraint in CompositeForeignKeyModel.table_constraints()
            if isinstance(constraint.branch, TableForeignKeyConstraint)
        ]
        assert len(constraints) == 1
        constraint = constraints[0]
        assert constraint.name == "fk_order_line"
        assert constraint.branch.columns == ["order_id", "line_no"]
        assert constraint.branch.references == (Table(None, "orders"), ["order_no", "line_no"])

    def test_columns_rejects_branch_without_table_counterpart(self):
        with pytest.raises(TypeError, match="table-level counterpart"):
            UseConstraint(ColumnNotNullConstraint, columns=["a", "b"])

    def test_single_column_form_is_unchanged(self):
        # Regression guard: the anchor-only form still yields a column-level
        # clause (alongside the implicit nullability constraint) and nothing
        # at table level.
        class WithColumnUnique(ActiveRecord):
            @classmethod
            def table_name(cls):
                return "with_column_unique"

            id: int
            code: Annotated[str, UseConstraint(ColumnUniqueConstraint, name="uq_code")]

        column_constraints = WithColumnUnique.column_constraints("code")
        unique_constraints = [
            constraint for constraint in column_constraints
            if isinstance(constraint.branch, ColumnUniqueConstraint)
        ]
        assert len(unique_constraints) == 1
        assert unique_constraints[0].name == "uq_code"
        assert all(
            not isinstance(constraint.branch, TableUniqueConstraint)
            for constraint in WithColumnUnique.table_constraints()
        )

    def test_anchor_not_first_is_rejected_at_class_creation(self):
        with pytest.raises(TypeError, match="leftmost"):
            class AnchorMismatch(ActiveRecord):
                @classmethod
                def table_name(cls):
                    return "anchor_mismatch"

                id: int
                status: Annotated[
                    str,
                    UseConstraint(ColumnUniqueConstraint, columns=["code", "status"]),
                ]
                code: str

    def test_unknown_column_is_rejected_at_class_creation(self):
        with pytest.raises(TypeError, match="does not define"):
            class UnknownColumn(ActiveRecord):
                @classmethod
                def table_name(cls):
                    return "unknown_column"

                id: int
                code: Annotated[
                    str,
                    UseConstraint(ColumnUniqueConstraint, columns=["code", "nope"]),
                ]
                status: str


class TestDirectWriteFaceStaysReadable:
    """D3b ordering: the annotation surface lands first, the direct-write
    ``__table_indexes__`` face keeps working until its own turn."""

    def test_table_indexes_declaration_is_returned_unchanged(self):
        class WithTableIndex(ActiveRecord):
            @classmethod
            def table_name(cls):
                return "with_table_index"

            __table_indexes__ = [
                IndexDefinition(None, name="idx_table_email", columns=["email"]),
            ]

            id: int
            email: str

        indexes = WithTableIndex.table_indexes()
        assert len(indexes) == 1
        assert indexes[0].name == "idx_table_email"


class TestSqliteBackendStillConstructs:
    """A backend still binds the model: declarations never break configure."""

    def test_model_configures_and_accessors_resolve(self, tmp_path):
        CompositeIndexModel.configure(
            SQLiteConnectionConfig(database=str(tmp_path / "decl.db")), SQLiteBackend
        )
        assert CompositeIndexModel.table_name() == "composite_index_model"
        assert CompositeIndexModel.backend() is not None
