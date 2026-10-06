# src/rhosocial/activerecord/backend/dialect/protocols/object/relation.py
"""Rendering the relations a query can read from."""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

from .namespace import NamespaceSupport

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.objects import (
        ForeignTable,
        MaterializedView,
        Table,
        View,
    )

__all__ = [
    "TableObjectSupport",
    "ViewObjectSupport",
    "MaterializedViewObjectSupport",
    "ForeignTableObjectSupport",
]


@runtime_checkable
class TableObjectSupport(NamespaceSupport, Protocol):
    """How a :class:`~....expression.objects.Table` is named."""

    def format_table_object(self, expr: "Table") -> Tuple[str, tuple]:
        """Render *expr* as a table name.

        The counterpart of :attr:`Table.format_method`. It renders the name the
        object is known by, never the statement that creates or drops it, which
        is what lets a statement hold a ``Table`` as an ordinary child.

        Args:
            expr: The table being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty, because an
            identifier is never a bind parameter.

        Raises:
            UnsupportedFeatureError: The table carries a namespace level this
                dialect declares it cannot express.
        """
        ...  # pragma: no cover


@runtime_checkable
class ViewObjectSupport(NamespaceSupport, Protocol):
    """How a :class:`~....expression.objects.View` is named."""

    def format_view_object(self, expr: "View") -> Tuple[str, tuple]:
        """Render *expr* as a view name.

        Distinct from ``format_create_view_statement``: that renders the
        statement, this renders the name an existing view is known by.

        Args:
            expr: The view being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty.

        Raises:
            UnsupportedFeatureError: The view carries a namespace level this
                dialect declares it cannot express.
        """
        ...  # pragma: no cover


@runtime_checkable
class MaterializedViewObjectSupport(NamespaceSupport, Protocol):
    """How a :class:`~....expression.objects.MaterializedView` is named."""

    def format_materialized_view_object(self, expr: "MaterializedView") -> Tuple[str, tuple]:
        """Render *expr* as a materialized view name.

        Separate from the view's because an engine may support materialized
        views without supporting views, or may spell the two differently.

        Args:
            expr: The materialized view being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty.

        Raises:
            UnsupportedFeatureError: The view carries a namespace level this
                dialect declares it cannot express.
        """
        ...  # pragma: no cover


@runtime_checkable
class ForeignTableObjectSupport(NamespaceSupport, Protocol):
    """How a :class:`~....expression.objects.ForeignTable` is named."""

    def format_foreign_table_object(self, expr: "ForeignTable") -> Tuple[str, tuple]:
        """Render *expr* as a foreign table name.

        The server the rows come from is named by the ``CREATE FOREIGN TABLE``
        statement and is not part of the name, so it is not rendered here.

        Args:
            expr: The foreign table being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty.

        Raises:
            UnsupportedFeatureError: The table carries a namespace level this
                dialect declares it cannot express.
        """
        ...  # pragma: no cover