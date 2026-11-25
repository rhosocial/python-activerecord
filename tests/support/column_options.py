# tests/support/column_options.py
"""Fake column options for the option-application contract tests.

Core's DummyDialect ships no ``ColumnOptions`` implementation, so these local
fakes stand in for a backend's pair: an option class that declares a custom
column-definition class and transfers its state through ``apply_to``.

The collation-bearing option appends a real ``CollationClause`` so the applied
state is visible in rendered SQL through the generic dialect formatter, not only
as an attribute on the column object.
"""

from rhosocial.activerecord.base import (
    ColumnOptions,
    DDLAnnotation,
    DDLAnnotationHandler,
)
from rhosocial.activerecord.backend.expression.statements import (
    CollationClause,
    ColumnDefinition,
)


class FakeColumnDefinition(ColumnDefinition):
    """A column-definition subclass selected by the fake options."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.applied_collations = []
        self.marker = None


class OtherColumnDefinition(ColumnDefinition):
    """A second column-definition subclass, for the conflicting-class case."""


class CollationOption(ColumnOptions):
    """Applies a collation clause and records it on the column."""

    def __init__(self, name):
        super().__init__()
        self.name = name

    def column_definition_class(self):
        return FakeColumnDefinition

    def apply_to(self, column):
        if not isinstance(column, FakeColumnDefinition):
            raise TypeError(
                "CollationOption.apply_to requires a FakeColumnDefinition, "
                f"got {type(column).__name__}"
            )
        column.attributes.append(CollationClause(column.dialect, self.name))
        column.applied_collations.append(self.name)


class MarkerOption(ColumnOptions):
    """Applies a plain marker attribute to the column."""

    def __init__(self, marker):
        super().__init__()
        self.marker = marker

    def column_definition_class(self):
        return FakeColumnDefinition

    def apply_to(self, column):
        if not isinstance(column, FakeColumnDefinition):
            raise TypeError(
                "MarkerOption.apply_to requires a FakeColumnDefinition, "
                f"got {type(column).__name__}"
            )
        column.marker = self.marker


class OtherOption(ColumnOptions):
    """Declares a different column-definition class."""

    def column_definition_class(self):
        return OtherColumnDefinition

    def apply_to(self, column):
        if not isinstance(column, OtherColumnDefinition):
            raise TypeError(
                "OtherOption.apply_to requires an OtherColumnDefinition, "
                f"got {type(column).__name__}"
            )


class BrokenOption(ColumnOptions):
    """Declares the fake class but always refuses to apply."""

    def column_definition_class(self):
        return FakeColumnDefinition

    def apply_to(self, column):
        raise TypeError("BrokenOption refuses every column")


class SilentOption(ColumnOptions):
    """Carries state but inherits the base no-op ``apply_to``."""

    def __init__(self, value):
        super().__init__()
        self.value = value

    def column_definition_class(self):
        return FakeColumnDefinition


class ColumnOptionAnnotation(DDLAnnotation):
    """Carries one or more column options for the handler to attach."""

    def __init__(self, *options):
        self.options = options


class ColumnOptionHandler(DDLAnnotationHandler):
    """Attaches the annotation's options to the field metadata."""

    annotation_types = (ColumnOptionAnnotation,)

    @classmethod
    def apply(cls, new_class, field_name, annotation, metadata):
        metadata.add_column_options(*annotation.options)
