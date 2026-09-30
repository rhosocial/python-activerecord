# tests/rhosocial/activerecord_test/feature/basic/fields/test_derived_field_markers.py
"""``UseColumn`` / ``UseAdapter`` on the annotation must not be dropped.

``DerivedField`` has two declaration forms, handled by
``DerivedFieldHandler._extract``:

* **Form A** -- ``ClassVar[DerivedField]`` plus a class-level assignment
* **Form B** -- ``ClassVar[Annotated[T, DerivedField(...), UseColumn(...), UseAdapter(...)]]``

``_extract`` returned at Form A before reading the annotation's metadata, so a
model declaring *both* -- Form B with a redundant assignment -- lost the
``UseColumn`` and ``UseAdapter`` silently: the SQL alias reverted to the field
name and the type adapter was not applied, with no warning.

Both forms now collect the markers first, so the two are interchangeable and the
``UseColumn`` collision check fires for either.
"""

from typing import ClassVar, Optional
from typing_extensions import Annotated

import pytest

from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.base import UseColumn
from rhosocial.activerecord.base.fields import DerivedField, UseAdapter
from rhosocial.activerecord.model import ActiveRecord


class PriceToInt:
    """Adapter that rounds, so ``UseAdapter`` is observable.

    Mirrors the shape of the fixture adapters: a plain class with
    ``to_database`` / ``from_database`` and a ``supported_types`` map.
    """

    def to_database(self, value, target_type, options=None):
        return float(value)

    def from_database(self, value, target_type, options=None):
        return int(round(value))

    @property
    def supported_types(self):
        return {int: {float}}


class FormAOnly(ActiveRecord):
    __table_name__ = "df_form_a"

    id: Optional[int] = None
    price: float = 0.0
    doubled: ClassVar[DerivedField] = DerivedField(lambda d: Column(d, "price") * Literal(d, 2))


class FormBOnly(ActiveRecord):
    __table_name__ = "df_form_b"

    id: Optional[int] = None
    price: float = 0.0
    doubled: ClassVar[
        Annotated[
            float,
            DerivedField(lambda d: Column(d, "price") * Literal(d, 2)),
            UseColumn("doubled_col"),
        ]
    ]


class FormAWithAnnotation(ActiveRecord):
    """Form B *plus* a class-level assignment -- the regressing shape."""

    __table_name__ = "df_form_a_annotated"

    id: Optional[int] = None
    price: float = 0.0
    doubled: ClassVar[
        Annotated[
            float,
            DerivedField(lambda d: Column(d, "price") * Literal(d, 2)),
            UseColumn("doubled_col"),
            UseAdapter(PriceToInt(), int),
        ]
    ] = DerivedField(lambda d: Column(d, "price") * Literal(d, 2))


class TestFormParity:
    def test_form_a_registers_the_derived_field(self):
        assert "doubled" in FormAOnly.__derived_fields__

    def test_form_b_registers_the_derived_field(self):
        assert "doubled" in FormBOnly.__derived_fields__

    def test_form_b_applies_use_column(self):
        assert FormBOnly.__derived_fields__["doubled"].column_name == "doubled_col"

    def test_form_a_with_annotation_applies_use_column(self):
        """The regression: the assignment used to shadow the annotation."""
        assert FormAWithAnnotation.__derived_fields__["doubled"].column_name == "doubled_col"

    def test_form_a_with_annotation_applies_use_adapter(self):
        adapter = FormAWithAnnotation.__derived_fields__["doubled"].adapter
        assert isinstance(adapter, PriceToInt)

    def test_form_a_without_markers_has_no_column_name(self):
        assert FormAOnly.__derived_fields__["doubled"].column_name is None

    def test_form_a_with_annotation_matches_form_b(self):
        """Form A + annotation must be indistinguishable from Form B."""
        assert (
            FormAWithAnnotation.__derived_fields__["doubled"].column_name
            == FormBOnly.__derived_fields__["doubled"].column_name
        )

    def test_the_assignment_is_not_mutated_by_marker_collection(self):
        """Form A copies before mutating, so the shared marker stays clean."""
        FormAWithAnnotation.__derived_fields__["doubled"]
        assert FormAOnly.__derived_fields__["doubled"].column_name is None


class TestColumnNameConflict:
    """The collision check must fire regardless of which form was used."""

    def test_conflict_raises_type_error_via_form_b(self):
        with pytest.raises(TypeError, match="conflicts with a regular field's column name"):

            class ConflictB(ActiveRecord):
                __table_name__ = "df_conflict_b"

                id: Optional[int] = None
                title: Annotated[str, UseColumn("shared")] = ""
                dup: ClassVar[Annotated[str, DerivedField(lambda d: Column(d, "title")), UseColumn("shared")]]

    def test_conflict_raises_type_error_via_form_a_with_annotation(self):
        with pytest.raises(TypeError, match="conflicts with a regular field's column name"):

            class ConflictA(ActiveRecord):
                __table_name__ = "df_conflict_a"

                id: Optional[int] = None
                title: Annotated[str, UseColumn("shared2")] = ""
                dup: ClassVar[
                    Annotated[str, DerivedField(lambda d: Column(d, "title")), UseColumn("shared2")]
                ] = DerivedField(lambda d: Column(d, "title"))
