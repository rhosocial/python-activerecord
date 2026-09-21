# src/rhosocial/activerecord/base/ddl/options.py
"""Dialect-free per-column options declaration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Type

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.statements import ColumnDefinition


class ColumnOptions:
    """Per-column options declaration carrying typed generic column settings.

    A plain declaration (not a renderable expression): the deriver maps its
    fields onto a ``ColumnDefinition`` of the class named by
    :meth:`column_definition_class`. Only **typed** fields are allowed — there
    is no ``dialect_options`` bag. Backend-specific column settings live on a
    backend's own ``XxxColumnOptions`` subclass, which overrides
    :meth:`column_definition_class` to return that backend's
    ``XxxColumnDefinition`` (and is rendered by the backend's
    ``format_column_definition``).

    Identity is **not** carried here: it migrated to the column-attribute
    channel (``Annotated[T, UseColumnAttributes(IdentityAttribute(...))]``),
    so the same semantic is never carried twice (§5.3).
    """

    def __init__(self):
        pass

    def column_definition_class(self) -> Type["ColumnDefinition"]:
        """The ``ColumnDefinition`` class this options declaration builds.

        Defaults to the generic ``ColumnDefinition``; backend option
        subclasses return their backend-specific column definition class so
        the deriver can assemble the right expression without the core
        importing any backend.
        """
        from rhosocial.activerecord.backend.expression.statements import (
            ColumnDefinition,
        )

        return ColumnDefinition

    def apply_to(self, column: "ColumnDefinition") -> None:
        """Transfer this declaration's backend-specific fields onto *column*.

        The generic declaration has no backend-specific fields, so this is a
        no-op. A backend ``XxxColumnOptions`` overrides it to set its typed
        fields on the matching ``XxxColumnDefinition`` (after the deriver has
        built the core column parts).
        """
